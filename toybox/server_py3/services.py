"""Google Service API classes."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import datetime
import logging
import time
from dateutil import parser
from googleapiclient import discovery
from googleapiclient import errors
import pytz
from google.cloud import datastore


RFC3339_FORMAT = '%Y-%m-%dT%H:%M:%SZ'  # RFC3339


def datetime_to_rfc3339(datetime_value):
  return datetime_value.strftime(RFC3339_FORMAT)


def rfc3339_to_datetime(string_value):
  return parser.parse(string_value)


def to_utc(value):
  return value.replace(tzinfo=pytz.utc)  # pylint: disable=g-tzinfo-replace


def to_tz_name(value, tz_name):
  return value.astimezone(pytz.timezone(tz_name))


EPOCH = to_utc(datetime.datetime.utcfromtimestamp(0))


def timezone_aware_now(*unused_args):
  return to_utc(datetime.datetime.utcnow())


class _DiscoveryUrlClientBuilder(object):
  """Builder for service clients from a Discovery URL."""

  def __init__(self, api_name, api_version, api_key, credentials):
    self._api_name = api_name
    self._api_version = api_version
    self._credentials = credentials
    self._client = discovery.build(
        self.api_name,
        self.api_version,
        developerKey=api_key,
        credentials=self.credentials,
        cache_discovery=False)

  @property
  def api_name(self):
    return self._api_name

  @property
  def api_version(self):
    return self._api_version

  @property
  def credentials(self):
    return self._credentials

  @property
  def client(self):
    return self._client


class _AbstractService(object):
  """Abstract service."""

  API_NAME = None
  API_VERSION = None
  API_KEY = None
  SCOPE = None

  def __init__(self, credentials, client=None):
    if client:
      self._client = client
    else:
      self._client = self.new_client(credentials)

  @classmethod
  def new_client(cls, credentials):
    assert cls.API_NAME, 'API_NAME is required'
    assert cls.API_VERSION, 'API_VERSION is required'
    assert cls.SCOPE, 'SCOPE is required'
    return _DiscoveryUrlClientBuilder(
        cls.API_NAME, cls.API_VERSION, cls.API_KEY, credentials).client

  @property
  def client(self):
    return self._client


class IdentityToolkitService(_AbstractService):
  """IdentityToolkit API."""

  API_NAME = 'identitytoolkit'
  API_VERSION = 'v3'
  SCOPE = 'https://www.googleapis.com/auth/identitytoolkit'

  _MAX_PAGE_SIZE = 1000

  def get_account_info_by_id(self, uid):
    body = {
        'localId': [uid]
    }
    result = self._client.relyingparty().getAccountInfo(
        body=body).execute()
    return result.get('users', [None])[0]

  def get_account_info_by_email(self, email):
    body = {
        'email': [email]
    }
    result = self._client.relyingparty().getAccountInfo(
        body=body).execute()
    return result.get('users', [None])[0]

  def download_account(self, page_token=None, max_results=None):
    if max_results is None:
      max_results = self._MAX_PAGE_SIZE
    assert max_results >= 1 and max_results <= self._MAX_PAGE_SIZE
    body = {
        'maxResults': max_results
    }
    if page_token:
      body.update({'nextPageToken': page_token})
    return self._client.relyingparty().downloadAccount(body=body).execute()


class FirebaseAdminService(IdentityToolkitService):
  """Firebase Admin API."""

  SCOPES = [
      IdentityToolkitService.SCOPE,
      'https://www.googleapis.com/auth/firebase.readonly'
  ]
  PROVIDER_ID_GOOGLE = 'google.com'

  def get_user(self, uid):
    return self.get_account_info_by_id(uid)

  def get_user_by_email(self, email):
    return self.get_account_info_by_email(email)

  def list_users(self, page_token=None, max_results=None):
    return self.download_account(
        page_token=page_token, max_results=max_results)

  def list_all_users(self):
    page_token = None
    while True:
      page = self.list_users(page_token=page_token)
      for user in page.get('users', []):
        yield user
      page_token = page['nextPageToken']
      if not page_token:
        break

  @classmethod
  def get_user_id_for(cls, federated_provider_id, user):
    for provider_info in user.get('providerUserInfo', {}):
      if provider_info.get('providerId') == federated_provider_id:
        return provider_info['federatedId']
    return None

  @classmethod
  def get_obfuscated_gaia_id(cls, user):
    return cls.get_user_id_for(cls.PROVIDER_ID_GOOGLE, user)


class DataLossPreventionService(_AbstractService):
  """Data Loss Prevention (DLP) API."""

  API_NAME = 'dlp'
  API_VERSION = 'v2'
  SCOPE = 'https://www.googleapis.com/auth/cloud-platform'

  # NOTE(psimakov): this API does not support 'projects/google.com:XYZ'
  # notation; so we decided to use well known hardcoded project
  PROJECT = 'a120-cdn'

  def list_info_type_names(self):
    """Lists all known detectable info types."""
    request = self._client.infoTypes().list()
    type_names = set()
    for item in request.execute().get('infoTypes', []):
      type_names.add(item['name'])
    return type_names

  def _info_types_for(self, type_names):
    type_info = []
    for name in type_names:
      type_info.append({
          'name': name
      })
    return type_info

  def inspect(self, project_id, content, type_names=None):
    """Inspects content for PII."""
    if not type_names:
      type_names = self.list_info_type_names()
    request = self._client.projects().content().inspect(
        parent=project_id,
        body={
            'inspectConfig': {
                'infoTypes': self._info_types_for(type_names)
            },
            'item': {
                'value': content,
            }
        }
    )
    return request.execute()


class LoggingService(_AbstractService):
  """Logging API."""

  API_NAME = 'logging'
  API_VERSION = 'v2'
  SCOPE = 'https://www.googleapis.com/auth/logging.admin'
  SCOPE_W = 'https://www.googleapis.com/auth/logging.write'

  SEVERITY_INFO = 'INFO'
  SEVERITY_WARNING = 'WARNING'
  SEVERITY_ERROR = 'ERROR'
  SEVERITY = set([SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR])

  LIST_PAGE_SIZE = 100

  ORDER_BY_ASC = 'timestamp asc'
  ORDER_BY_DESC = 'timestamp desc'

  _SORT_ORDER = set([ORDER_BY_ASC, ORDER_BY_DESC])

  def older_than_date_filter(self, start_datetime, field_name='timestamp'):
    """Formats date filter."""
    # TODO(psimakov): we may loose record here
    # datastore trims milliseconds from datetime; this is very bad news; it
    # causes us to have infinite loop and make no progress
    #
    # consider the following example:
    #   imagine we received the last entry from the log service with timestamp
    #   2018-02-05T05:12:59.787287Z; we put it into Datastore and it gets
    #   truncated to 2018-02-05T05:12:59Z; now we query for timestamp over
    #   2018-02-05T05:12:59Z and get that last entry 2018-02-05T05:12:59.787287Z
    #   again; we save it again; we query again... infinite loop, no progress
    #
    # if we round up milliseconds, we can skip some entrie, but we will not get
    # into infinite loop
    start_datetime = start_datetime.replace(microsecond=0) + datetime.timedelta(
        seconds=1)
    return '{field_name} >= "{start_datetime}"'.format(
        field_name=field_name,
        start_datetime=datetime_to_rfc3339(start_datetime)
    )

  def date_range_filter(self, start_datetime, end_datetime,
                        field_name='timestamp'):
    return '{field_name} >= "{start}" AND {field_name} <= "{end}"'.format(
        field_name=field_name,
        start=datetime_to_rfc3339(start_datetime),
        end=datetime_to_rfc3339(end_datetime)
    )

  def list_entries(self, resource_name, afilter=None, page_size=None,
                   order_by=None, limit=None):
    """Lists entries."""
    page_size = page_size if page_size else self.LIST_PAGE_SIZE
    page_token = None
    count = 0
    while True:
      body = {}
      body['resourceNames'] = [resource_name]
      if afilter:
        body['filter'] = afilter
      if page_size:
        body['pageSize'] = page_size
      if page_token:
        body['pageToken'] = page_token
      if order_by:
        assert order_by in self._SORT_ORDER, order_by
        body['orderBy'] = order_by
      request = self._client.entries().list(body=body)
      response = request.execute()
      page_token = response.get('nextPageToken', None)
      entries = response.get('entries', [])
      for entry in entries:
        yield entry
        count += 1
        if limit and limit <= count:
          return
      if not page_token:
        return

  def write_entry(self, from_project_id, from_module_id, to_project_id,
                  severity, message, args):
    assert severity in self.SEVERITY
    self._client.entries().write(body={
        'entries': [{
            'logName': (
                'projects/{project_id}/logs/'
                'cloudresourcemanager.googleapis.com%2F'
                'activity'
            ).format(project_id=to_project_id),
            'resource': {
                'type': 'gae_app',
                'labels': {
                    'project_id': from_project_id,
                    'module_id': from_module_id,
                    'version_id': 'prod'
                }
            },
            'severity': severity,
            'json_payload': {
                'message': message,
                'args': args
            }
        }],
        'partialSuccess': False,
    }).execute()


class MonitoringService(_AbstractService):
  """Monitoring API."""

  API_NAME = 'monitoring'
  API_VERSION = 'v3'
  SCOPE = 'https://www.googleapis.com/auth/monitoring'

  def get_metric(self, project_id, name, duration_sec, resolution_sec,
                 series_reducer, series_aligner):
    """Gets metrics data."""
    end = timezone_aware_now()
    start = end - datetime.timedelta(seconds=duration_sec)
    request = self._client.projects().timeSeries().list(
        name=project_id,
        filter='metric.type="%s"' % name,
        interval_startTime=datetime_to_rfc3339(start),
        interval_endTime=datetime_to_rfc3339(end),
        aggregation_crossSeriesReducer=series_reducer,
        aggregation_perSeriesAligner=series_aligner,
        aggregation_alignmentPeriod='%ss' % resolution_sec,
    )
    return request.execute()

  def get_sum_metric(self, project_id, name, duration_sec, resolution_sec):
    return self.get_metric(project_id, name, duration_sec, resolution_sec,
                           'REDUCE_SUM', 'ALIGN_SUM')

  def get_mean_metric(self, project_id, name, duration_sec, resolution_sec):
    return self.get_metric(project_id, name, duration_sec, resolution_sec,
                           'REDUCE_SUM', 'ALIGN_MEAN')


class DatastoreService(_AbstractService):
  """Datastore API."""

  API_NAME = 'datastore'
  API_VERSION = 'v1'
  SCOPE = 'https://www.googleapis.com/auth/datastore'

  def __init__(self, credentials, namespace, project_id):
    client = datastore.Client(
        credentials=credentials,
        namespace=namespace,
        project=project_id)
    super(DatastoreService, self).__init__(None, client=client)

  def query(self, kind, order=None):
    return self._client.query(kind=kind, order=order)

  def entity(self, key):
    return datastore.Entity(key=key)


class BigQueryService(_AbstractService):
  """BigQuery API."""

  API_NAME = 'bigquery'
  API_VERSION = 'v2'
  SCOPE = 'https://www.googleapis.com/auth/bigquery'

  _JOB_STATE_DONE = 'DONE'
  _JOB_STATE = set(['PENDING', 'RUNNING', _JOB_STATE_DONE])
  _MAX_DEFAULT_LIST_RESULTS = 500
  _WAIT_DELAY_SEC = 3

  def __init__(self, credentials, project_id):
    self._project_id = project_id
    super(BigQueryService, self).__init__(credentials)

  def dataset_exists(self, dataset_id):
    """Checks if dataset exists."""
    request = self._client.datasets().get(
        projectId=self._project_id,
        datasetId=dataset_id)
    try:
      request.execute()
      return True
    except errors.HttpError as e:
      if int(e.resp.status) == 404:
        return False
      raise

  def dataset_insert(self, dataset_id, desc):
    self._client.datasets().insert(
        projectId=self._project_id,
        body={
            'datasetReference': {
                'projectId': self._project_id,
                'datasetId': dataset_id,
            },
            'description': desc,
        }
    ).execute()

  def dataset_delete(self, dataset_id):
    self._client.datasets().delete(
        projectId=self._project_id,
        datasetId=dataset_id,
        deleteContents=True
    ).execute()

  def list_tables(self, dataset_id):
    """Lists all dataset tables."""
    return self._client.tables().list(
        projectId=self._project_id,
        datasetId=dataset_id,
        maxResults=self._MAX_DEFAULT_LIST_RESULTS).execute()

  def table_exists(self, table_id, dataset_id):
    """Checks if table exists."""
    request = self._client.tables().get(
        projectId=self._project_id,
        datasetId=dataset_id,
        tableId=table_id)
    try:
      request.execute()
      return True
    except errors.HttpError as e:
      if int(e.resp.status) == 404:
        return False
      raise

  def table_update_desc(self, table_id, dataset_id, new_desc):
    self._client.tables().update(
        projectId=self._project_id,
        datasetId=dataset_id,
        tableId=table_id,
        body={
            'tableReference': {
                'projectId': self._project_id,
                'datasetId': dataset_id,
                'tableId': table_id,
            },
            'description': new_desc,
        }
    ).execute()

  def table_insert(self, table_id, desc, dataset_id, schema):
    self._client.tables().insert(
        projectId=self._project_id,
        datasetId=dataset_id,
        body={
            'tableReference': {
                'projectId': self._project_id,
                'datasetId': dataset_id,
                'tableId': table_id,
            },
            'description': desc,
            'schema': schema,
        }
    ).execute()

  def table_delete(self, table_id, dataset_id):
    self._client.tables().delete(
        projectId=self._project_id,
        datasetId=dataset_id,
        tableId=table_id
    ).execute()

  def _table_insert_many(self, table_id, rows, dataset_id):
    return self._client.tabledata().insertAll(
        projectId=self._project_id,
        datasetId=dataset_id,
        tableId=table_id,
        body={
            'rows': rows
        },
        fields='insertErrors'
    ).execute()

  def table_insert_all(self, table_id, rows, dataset_id):
    """Insert rows into table."""
    def _try_once():
      result = self._table_insert_many(table_id, rows, dataset_id)
      if result.get('insertErrors'):
        raise Exception('Error inserting batch into %s: %s' % (
            dataset_id, result))
      return result

    try:
      return _try_once()
    except Exception as e:
      text = str(e)
      bad_gateway_error = 'HttpError 502' in text and '"Bad Gateway"' in text
      socket_error = 'Unable to connect to server at URL' in text
      if socket_error or bad_gateway_error:
        logging.info('Retrying _table_insert_many(): %s',
                     'socket error' if socket_error else 'bad gateway')
        return _try_once()
      raise

  def query(self, sql):
    return self._client.jobs().query(
        projectId=self._project_id,
        body={
            'useLegacySql': False,
            'query': sql
        }
    ).execute()

  def _check_result(self, result, no_wait):
    """Waits for job to complete."""
    job_id = result.get('jobReference', {}).get('jobId')
    while True:
      status = result.get('status', {})
      assert 'errorResult' not in status, (
          'Error executing job "%s":\n%s' % (job_id, status))

      state = status.get('state')
      assert state in self._JOB_STATE, 'Bad job state for:\n%s' % result
      if status.get('state') == self._JOB_STATE_DONE or no_wait:
        return result

      assert job_id, 'No jobId for:\n%s' % result
      time.sleep(self._WAIT_DELAY_SEC)
      result = self._client.jobs().get(
          projectId=self._project_id, jobId=job_id).execute()

  def extract_table(self, table_id, dataset_id, resource_uri, no_wait=True):
    """Extracts table into gs://..."""
    result = self._client.jobs().insert(
        projectId=self._project_id,
        body={
            'configuration': {
                'extract': {
                    'sourceTable': {
                        'projectId': self._project_id,
                        'datasetId': dataset_id,
                        'tableId': table_id
                    },
                    'destinationUris': [
                        resource_uri
                    ],
                    'destinationFormat': 'NEWLINE_DELIMITED_JSON'
                }
            }
        }).execute()
    return self._check_result(result, no_wait)

  def copy_table(self, existing_table_id, new_table_id, dataset_id,
                 no_wait=True):
    """Makes a copy of a table."""
    result = self._client.jobs().insert(
        projectId=self._project_id,
        body={
            'configuration': {
                'copy': {
                    'sourceTable': {
                        'projectId': self._project_id,
                        'datasetId': dataset_id,
                        'tableId': existing_table_id
                    },
                    'destinationTable': {
                        'projectId': self._project_id,
                        'datasetId': dataset_id,
                        'tableId': new_table_id
                    },
                }
            }
        }).execute()
    return self._check_result(result, no_wait)


class SheetsService(_AbstractService):
  """Sheets API."""

  API_NAME = 'sheets'
  API_VERSION = 'v4'
  SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly'
  SCOPE_W = 'https://www.googleapis.com/auth/spreadsheets'

  def get_values(self, sheet_id, value_range):
    cmd = self._client.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=value_range,
        valueRenderOption='FORMATTED_VALUE',
        majorDimension='ROWS'
    )
    return cmd.execute()

  @classmethod
  def values_to_list_of_dicts(cls, values):
    """Converts values into dict or dicts, keyed by column name."""
    items = []
    headers = None
    for row in values:
      if headers is None:
        headers = values[0]
        continue
      name_value = {}
      index = 0
      for value in row:
        name_value[headers[index]] = value
        index += 1
      items.append(name_value)
    return items

  @classmethod
  def values_to_dict_of_dicts(cls, values, key_col_name):
    """Converts values into dict or dicts, keyed by column name."""
    dict_of_dicts = {}
    headers = None
    for row in values:
      if headers is None:
        headers = values[0]
        continue
      name_value = {}
      index = 0
      for value in row:
        name_value[headers[index]] = value
        index += 1
      key = name_value[key_col_name]
      assert key not in dict_of_dicts, key
      dict_of_dicts[key] = name_value
    return dict_of_dicts

  def get_sheet(self, sheet_id, include_grid_data=True):
    cmd = self._client.spreadsheets().get(
        spreadsheetId=sheet_id,
        includeGridData=include_grid_data
    )
    return cmd.execute()

  def clear_sheet(self, sheet_id, value_range):
    cmd = self._client.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=value_range,
        body={}
    )
    return cmd.execute()

  def update_sheet(self, sheet_id, value_range, value_range_body,
                   value_input_option='USER_ENTERED', replace_none_with=None):
    """Updates sheet."""
    # the None cell values are ignored during updates;
    # turn them into something else if merge is not desired
    if replace_none_with is not None:
      rows = []
      for values in value_range_body['values']:
        row = []
        for value in values:
          row.append(value if value is not None else replace_none_with)
        rows.append(row)
      value_range_body['values'] = rows
    cmd = self._client.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=value_range,
        valueInputOption=value_input_option,
        body=value_range_body
    )
    return cmd.execute()

  def append_sheet(self, sheet_id, value_range, value_range_body,
                   value_input_option='USER_ENTERED',
                   insert_data_option='INSERT_ROWS'):
    """Appends values."""
    cmd = self._client.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=value_range,
        valueInputOption=value_input_option,
        insertDataOption=insert_data_option,
        body=value_range_body
    )
    return cmd.execute()


def _colnum_string(n):
  string = ''
  while n > 0:
    n, remainder = divmod(n - 1, 26)
    string = chr(65 + remainder) + string
  return string


def _init_column_names():
  """Initializes column names and their mapping to column index."""
  mapping = {}
  names = []

  index = 1
  while index < 256:
    name = _colnum_string(index)
    names.append(name)
    mapping[name] = index
    index += 1
  return names, mapping


class SheetParser(object):
  """Helper clsass to parse sheet data."""

  SHEET_TO_PYTHON_DATE_FORMAT = {
      'm/d/yyyy': '%m/%d/%Y',
      'yyyy/m/d': '%Y/%m/%d',
      'yyyy-m-d': '%Y-%m-%d',
      'yyyy"-"mm"-"dd': '%Y-%m-%d',  # ugly... maybe this is user entered?
  }

  _COLUMN_NAMES, _COLUMN_NAME_TO_INDEX = _init_column_names()

  def __init__(self, data):
    assert 'sheets' in data
    self._data = data

  @classmethod
  def col_index_for(cls, name):
    return cls._COLUMN_NAME_TO_INDEX[name]

  @classmethod
  def col_name_for(cls, index):
    assert index > 0
    return cls._COLUMN_NAMES[index - 1]

  def sheet(self, sheet_index):
    assert sheet_index >= 0
    sheets = self._data['sheets']
    if sheet_index >= len(sheets):
      return None
    return sheets[sheet_index]

  def sheets(self):
    index = 0
    for _ in self._data['sheets']:
      yield index
      index += 1

  def rows(self, sheet_index):
    index = 0
    for _ in self._data['sheets'][sheet_index]['data'][0]['rowData']:
      yield index
      index += 1

  def sheet_count(self):
    return len(self._data['sheets'])

  def row_count(self, sheet_index):
    return self._data['sheets'][sheet_index][
        'properties']['gridProperties']['rowCount']

  def col_count(self, sheet_index):
    return self._data['sheets'][sheet_index][
        'properties']['gridProperties']['columnCount']

  def row(self, sheet_index, row_index):
    return self._data['sheets'][sheet_index]['data'][0]['rowData'][row_index]

  def hyperlink(self, sheet_index, row_index, column_index):
    """Extracts cell hyperlink value."""
    row = self.row(sheet_index, row_index)
    if 'values' not in row:
      return None
    if len(row['values']) <= column_index:
      return None
    return row['values'][column_index].get('hyperlink')

  def cell(self, sheet_index, row_index, column_index, get_as_string=False):
    """Extracts cell value."""
    try:
      row = self.row(sheet_index, row_index)
      if 'values' not in row:
        return None
      if len(row['values']) <= column_index:
        return None

      if get_as_string:
        cell_data = row['values'][column_index]
        if 'formattedValue' in cell_data.keys():
          return cell_data['formattedValue']
        elif 'effectiveValue' in cell_data.keys():
          return cell_data['effectiveValue'].values()[0]
        else:
          return None

      aformat = row['values'][column_index].get('userEnteredFormat')
      if aformat:
        if 'DATE' == aformat.get('numberFormat', {}).get('type', {}):
          pattern = aformat['numberFormat']['pattern']
          value = row['values'][column_index].get('formattedValue')
          if value:
            return datetime.datetime.strptime(
                value, self.SHEET_TO_PYTHON_DATE_FORMAT[pattern])

      return row['values'][column_index].get(
          'effectiveValue', {None: None}).values()[0]
    except Exception as e:  # pylint: disable=broad-except
      raise Exception('Failed to get cell(%s, %s, %s):\n%s' % (
          sheet_index, row_index, column_index, e))

  def to_grid_map(self, sheet_index):
    """Converts sheet into dict of dicts."""
    rows = {}
    for rindex in xrange(0, self.row_count(sheet_index)):
      values = {}
      for cindex in xrange(0, self.col_count(sheet_index)):
        value = self.cell(sheet_index, rindex, cindex)
        if value:
          values[str(cindex)] = value
      if values:
        rows[str(rindex)] = values
    return rows


class PlusService(_AbstractService):
  """Google Plus API."""

  API_NAME = 'plus'
  API_VERSION = 'v1'
  SCOPE = 'https://www.googleapis.com/auth/plus.login'

  def get_person(self, user_id):
    return self._client.people().get(userId=user_id).execute()
