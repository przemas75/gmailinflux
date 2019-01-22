
from __future__ import print_function
import base64
import email
import re
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import time
from influxdb import InfluxDBClient

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
DATABASE='testowa'
HOST='172.16.8.7'
PORT=8086
USER='admin'
PASSWORD='pass'
NLABEL = 'cafe'

#def remove_punctuation(text):
#   return text

#def concat_email_text(mime_msg):
#    text = ""
#    for part in mime_msg.walk():
#        payload = part.get_payload(decode=True)
#        if payload is not None:
#            text += " "
#            text += payload
#    return text

#def html_to_text(html_page_string):
#    html_page_string = Cleaner(style=True).clean_html(html_page_string)
#    soup = BeautifulSoup(html_page_string)
#    return " ".join(soup.findAll(text=True))

def write_to_influx(text, data):
        myclient = InfluxDBClient(host=HOST, port=PORT, username=USER, password=PASSWORD, database=DATABASE)
        pattern = ' %d %b %Y %H:%M:%S '
        data = int(time.mktime(time.strptime(data, pattern))) * 1000000000
        valu = float(text)
        influx_metric = [{
             'measurement': 'kwh_cafe',
             'time': data,
             'fields': {
                   'value': valu
             }
        }]
        myclient.write_points(influx_metric)

def main():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()))

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    for label in labels:
        if label['name'] == NLABEL:
              labelid = label['id']
    response = service.users().messages().list(userId='me', labelIds=[labelid]).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])
   
    while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId='me',
                       labelIds=labelid, pageToken=page_token).execute()
            messages.extend(response['messages'])

    for msg in messages:
        message = service.users().messages().get(userId='me', id=msg['id'], format='raw').execute()
        message = base64.urlsafe_b64decode(message['raw'].encode('ascii'))
        mime_msg = email.message_from_string(message)
        data = mime_msg.get("Date")
        data = re.search('^(.*),(.*)\\+(.*)$', data).group(2)
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/plain':
                #text = (part.get_payload())
                text = ''.join(str(part.get_payload()))
                text = re.sub('[^0-9.]', "", text, flags=re.M)
                print(data, text)
                try:
                   write_to_influx(text, data)
                except:
                    print("There is problem with value:", text)
                    continue

if __name__ == '__main__':
    main()
