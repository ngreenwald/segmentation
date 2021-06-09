import os
import json
import io

import pandas as pd

import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

_SCOPES = ['https://www.googleapis.com/auth/drive']

_FOLDER_MIME_CHECK = "mimeType = 'application/vnd.google-apps.folder'"
_FILE_MIME_CHECK = "mimeType != 'application/vnd.google-apps.folder'"
_SHORTCUT_MIME_CHECK = "mimeType = 'application/vnd.google-apps.shortcut'"

_FOLDER_MIME = "application/vnd.google-apps.folder"

SERVICE = None

def _gen_enckey(pw):
    pw = pw.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'.\x03\x95d\x19\xc3o(L\xc3T\x12\xfd \xb1\x95',
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(pw))

def _decrypt_cred_data(data, pw):
    fernet = Fernet(_gen_enckey(pw))
    data_out = None

    try:
        data_out = fernet.decrypt(data)
    except InvalidToken as e:
        print("Invalid Key - Could not retrieve credentials...")
    
    if data_out is not None:
        data_out = json.loads(data_out)

    return data_out

def init_google_dirve_api(auth_pw):
    """Initializes the google drive api service

    Args:
        auth_pw (str): Encryption pw used to generate key for google drive api usage
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/.toks/.token.json'):
        creds = Credentials.from_authorized_user_file('/home/.toks/.token.json', _SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # read encrypted file data
            with open('/home/.toks/.creds.enc', 'rb') as f:
                data = f.read()

            # decrypt via user provided key
            client_config = _decrypt_cred_data(data, auth_pw)
            if client_config is None:
                return

            # generate oauth2 session
            flow = InstalledAppFlow.from_client_config(client_config, _SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('/home/.toks/.token.json', 'w') as token:
            token.write(creds.to_json())

    global SERVICE
    SERVICE = build('drive', 'v3', credentials=creds)

def _validate(path_string):
    global SERVICE
    if path_string[0] != '/':
        print(f'Invalid path provided.  Please use the format: /path/to/folder')
        return None, None

    parents = path_string.split('/')[1:-1]
    ids = ['root']

    # validate parent existence
    for i, parent in enumerate(parents):
        if parent == '':
            continue
        response = SERVICE.files().list(
            q=f"(('{ids[-1]}' in parents) and (name = '{parent}') and (({_FOLDER_MIME_CHECK}) or ({_SHORTCUT_MIME_CHECK})))",
            spaces='drive',
            fields='files(id, shortcutDetails(targetId))',
        ).execute()

        files = response.get('files', [])
        if len(files) == 0:
            print(f'Could not find the folder {parent} in parent folder {parents[i - 1]}...')
            return None, None
        
        # if shortcut, get target id
        if files[0].get('shortcutDetails', None) is not None:
            ids.append(files[0].get('shortcutDetails').get('targetId'))
        else:
            ids.append(files[0].get('id'))

    # validate file existence
    response = SERVICE.files().list(
        q=f"(('{ids[-1]}' in parents) and (name = '{path_string.split('/')[-1]}'))",
        spaces='drive',
        fields='files(id, shortcutDetails(targetId))'
    ).execute()
    files = response.get('files', [])

    # transform ids into map
    ids = dict(zip(['root'] + parents, ids))

    # return appropriate result
    if len(files) == 0:
        return ids, None

    # if shortcut, get target id
    if files[0].get('shortcutDetails', None) is not None:
        return ids, files[0].get('shortcutDetails').get('targetId')
    else:
        return ids, files[0].get('id')

class GoogleDrivePath(object):
    def __init__(self, path_string):
        self.bad_service = False
        global SERVICE
        if self._service_check():
            print("""
            Warning: Please call `init_google_drive_api` with the appropriate password, in order to
                     use GoogleDrivePath's.
            """)
            self.bad_service = True
            self.path_string = None
            self.parent_id_map = {}
            self.fileID = None
            return super().__init__()

        self.path_string = path_string
        self.parent_id_map, self.fileID = _validate(path_string)
        return super().__init__()

    def __truediv__(self, more_path):
        new_path_string = self.path_string + '/' + more_path
        return GoogleDrivePath(new_path_string)

    def _service_check(self):
        global SERVICE
        return SERVICE is None or self.bad_service

    def clone(self, dest, overwrite=False):
        """ Clones directory structure into provided destination

        For a given path_string, e.g '/root/folderA/folderB', all files and subdirectories of
        'folderB' are cloned into the destination.

        Args:
            dest (str):
                A path location to contain cloned directory structure.  Must be a directory.
            overwrite (bool):
                If files are already present in dest and overwrite is False, no cloning is
                performed.  Otherwise, the directory is overwriten with the cloned data.
        """
        if self._service_check() or self.fileID is None:
            return
        
        ## TODO: implement this

        return

    def upload(self, src, overwrite=False):
        """ Uploads contents and file structure of local directory to Drive.

        For a given path_string, e.g '/root/folderA/folderB', the provided source file, as well as
        all of its contents, will be added into 'folderB'.

        Args:
            src (str):
                A path location to copy a directory structure/content from.  Doesn't need to be a
                directory.
            overwrite (bool):
                If similarly named content exists on Drive, overwrite is False, no upload will take
                place.  Otherwise, the content on the Drive folder is updated/overwritten.
        """
        if self._service_check() or self.parent_id_map is None:
            return

        ## TODO: implement this

        return

    def read(self):
        """ Returns given file data if path leads to a file

        Returns:
            BytesIO: file data bytes.
        """
        if self._service_check() or self.fileID is None:
            return None

        global SERVICE
        request = SERVICE.files().get_media(fileId=self.fileID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f'Downloading {self.path_string} - {int(status.progress() * 100)}% ...')
        fh.seek(0)
        return fh

    def read_csv(self, **kwargs):
        """ Reads csv from Drive and returns a pandas dataframe

        Args:
            **kwargs (dict): Arguments passed to `pandas.read_csv()` function.
        
        Returns:
            DataFrame: pandas dataframe from read csv
        """
        if self.path_string.split('/')[-1].endswith('.csv'):
            data = self.read()
            if data is not None:
                return pd.read_csv(data, **kwargs)
        return None

    def write(self, data, overwrite=False):
        """ Writes file data or data from file path to provided Drive file.

        Args:
            data (str or BytesIO):
                If BytesIO, data is directly uploaded.  If str, data is assumed to be a filepath
                and data is attempted to be read from the file.
            overwrite (bool):
                If a file already exists at the path_string and overwrite is False, no data is
                written.  Otherwise, the existing file on Drive is updated/overwritten.
        """
        if self._service_check() or self.parent_id_map is None:
            return

        ## TODO: implement this
        return

    def lsfiles(self):
        if self._service_check() or self.fileID is None:
            return None

        filenames = []

        global SERVICE
        page_token = None
        while True:
            response = SERVICE.files().list(
                q=f"(('{self.fileID}' in parents) and ({_FILE_MIME_CHECK}))",
                spaces='drive',
                fields='nextPageToken, files(name, mimeType, shortcutDetails(targetMimeType))',
                pageToken=page_token).execute()

            for file in response.get('files', []):
                if file.get('shortcutDetails', None) is not None:
                    mimeType = file.get('shortcutDetails').get('targetMimeType')
                    if mimeType != _FOLDER_MIME:
                        filenames.append(file.get('name'))
                else:    
                    filenames.append(file.get('name'))

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return filenames

    def lsdirs(self):
        if self._service_check() or self.fileID is None:
            return None

        dirnames = []

        global SERVICE
        page_token = None
        while True:
            response = SERVICE.files().list(
                q=f"(('{self.fileID}' in parents) and (({_FOLDER_MIME_CHECK}) or ({_SHORTCUT_MIME_CHECK})))",
                spaces='drive',
                fields='nextPageToken, files(name, shortcutDetails(targetMimeType))',
                pageToken=page_token).execute()

            for file in response.get('files', []):
                if file.get('shortcutDetails', None) is not None:
                    mimeType = file.get('shortcutDetails').get('targetMimeType')
                    if mimeType == _FOLDER_MIME:
                        dirnames.append(file.get('name'))

                dirnames.append(file.get('name'))

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return dirnames

def path_join(*path_parts, get_filehandle=False):
    google_drive_path = type(path_parts[0]) is GoogleDrivePath

    if not google_drive_path:
        return os.path.join(path_parts[0], *path_parts[1:])

    path_parts_filt = [
        pp
        for pp in path_parts[1:]
        if pp != ""
    ]

    path_out = path_parts[0] / '/'.join(path_parts_filt)
    if get_filehandle:
        return path_out.read()

    return path_out
