#!/usr/bin/python2
'''
Based on http://jeremyblythe.blogspot.co.uk code
2015-05-29: changed to use official Python wrapper from Google to avoid deprecated ClientLogin (stef@nstrahl.de)

== Installation of PyDrive and OAuth2 ==
> apt-get install python-pip
> pip install PyDrive

== Step 1: register pydrive itself ==
Go to https://code.google.com/apis/console (you need to be logged into Google)
Create your own project (e.g. 'pydrive').
On "APIs & auth -> APIs" menu enable Drive API
On "APIs & auth -> Credentials" menu, create OAuth2.0 Client ID.
Select Application type to be a "Installed application" and type "other"
Download JSON file
rename to client_secrets.json and copy in same path as this python script

== Step 2: obtain OAuth2.0 authorization key for our Google Account ==
> python
>>> from pydrive.auth import GoogleAuth
>>> from pydrive.drive import GoogleDrive
>>> gauth = GoogleAuth()
>>> gauth.CommandLineAuth()
Visit Webpage as instructed and copy&pase verification key
>>> gauth.SaveCredentialsFile("pydrive_auth.txt")

Motion Uploader - uploads pictures & videos to Google Drive
'''

import smtplib
from datetime import datetime
import os.path
import sys
import ConfigParser

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

class MotionUploader:
    def __init__(self, config_file_path):
        # Load config
        config = ConfigParser.ConfigParser()
        config.read(config_file_path)
        
        # GMail account credentials
        self.username = config.get('gmail', 'user')
        self.password = config.get('gmail', 'password')
        self.from_name = config.get('gmail', 'name')
        self.sender = config.get('gmail', 'sender')
        
        # Recipient email address (could be same as from_addr)
        self.recipient = config.get('gmail', 'recipient').split(';')
        self.snapshotrecipient = config.get('gmail', 'snapshotrecipient').split(';')
        
        # Subject line for email
        self.subject = config.get('gmail', 'subject')
        
        # First line of email message
        self.message = config.get('gmail', 'message')
                
        # Folder (or collection) in Docs where you want the pictures & videos to go
        self.folder = config.get('docs', 'folder')
        
        # Options
        self.delete_after_upload = config.getboolean('options', 'delete-after-upload')
        self.send_email = config.getboolean('options', 'send-email')
        
        self._create_gdata_client()

    def _create_gdata_client(self):
        """Create a pydrive oonnection."""
	
	self.gauth = GoogleAuth()
	self.gauth.LoadCredentialsFile("pydrive_auth.txt")
	if self.gauth.credentials is None:  
    	    self.gauth.CommandLineAuth()  # Authenticate if they're not there
	elif self.gauth.access_token_expired:  
            self.gauth.Refresh()          # Refresh them if expired
        else:                               
            self.gauth.Authorize()        # Initialize the saved creds
        self.gauth.SaveCredentialsFile("pydrive_auth.txt")  # Save the current credentials to a file
        self.drive = GoogleDrive(self.gauth)# Initialize the saved creds

    def _get_folder_resource(self):
        """Find and return the resource whose title matches the given folder."""
        return self.drive.ListFile({'q': "title='{}' and mimeType contains 'application/vnd.google-apps.folder' and trashed=false".format(self.folder)}).GetList()[0]
    
    def _send_email(self,msg):
        '''Send an email using the GMail account.'''
        senddate=datetime.strftime(datetime.now(), '%Y-%m-%d')
        m="Date: %s\r\nFrom: %s <%s>\r\nTo: %s\r\nSubject: %s\r\nX-Mailer: My-Mail\r\n\r\n" % (senddate, self.from_name, self.sender, ", ".join(self.recipient), self.subject)
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(self.username, self.password)
        server.sendmail(self.sender, self.recipient, m+msg)
        server.quit()    

    def media_upload(self, file_path, folder_resource):
        '''Upload the file and return the doc'''
	print('Uploading image')
        doc = self.drive.CreateFile({'title':os.path.basename(file_path), 'parents':[{u'id': folder_resource['id']}]})
	doc.SetContentFile(file_path)
	doc.Upload()
        return doc
    
    def upload_file(self, file_path):
        """Upload a picture / video to the specified folder. Then optionally send an email and optionally delete the local file."""
        folder_resource = self._get_folder_resource()
        if not folder_resource:
            raise Exception('Could not find the %s folder' % self.folder)

        doc = self.media_upload(file_path, folder_resource)
                      
        if self.send_email:
            if file_path.split('.')[-2][-8:] == 'snapshot':
                self.recipient = self.recipient + self.snapshotrecipient

            thumbnail_link = doc['thumbnailLink'] # unused at the moment
	    media_link = doc['alternateLink']

            # Send an email with thumbnail and link
            msg = self.message
            msg += '\n\n' + media_link
            self._send_email(msg)    

        if self.delete_after_upload:
            os.remove(file_path)

if __name__ == '__main__':         
    try:
        if len(sys.argv) < 3:
            exit('uploads pictures / videos to Google Drive\n Usage: uploader.py {config-file-path} {media-file-path}')
        cfg_path = sys.argv[1]
        media_path = sys.argv[2]    
        if not os.path.exists(cfg_path):
            exit('Config file does not exist [%s]' % cfg_path)    
        if not os.path.exists(media_path):
            exit('Picture / Video file does not exist [%s]' % media_path)    
        MotionUploader(cfg_path).upload_file(media_path)
    except Exception as e:
        exit('Error: [%s]' % e)
