#!/usr/bin/python3
################################################################################
# remote.py - command-line youtube leanback remote
# A command-line interface YouTube Leanback Remote. Available under the ISC
# license.
#
# https://github.com/mutantmonkey/youtube-remote
# author: mutantmonkey <mutantmonkey@mutantmonkey.in>
################################################################################

import config
import json
import requests
#import urlparse
import urllib.parse
import sys
import pprint
import uuid
import random 
import string

def rand_str(length):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def zx():
    return rand_str(12)


class RID(object):
    def __init__(self):
        self.Reset()

    def Reset(self):
        self.number = random.randrange(10000,99999)
 
    def Next(self):
        self.number = self.number+1
        return self.number

class YouTubeLoungeSession(object):
	def __init__(self, sid = None, gsession = None):
		self.sid = sid
		self.gsession = gsession
		self.ofs = 0
		self.setAID(5)

	def getOfs(self):
		ofs = self.ofs;
		self.ofs = ofs+1
		return ofs

	def setSid(self, sid):
		self.sid = sid;

	def setGsession(self, gsession):
		self.gsession = gsession

	def getAID(self):
		return self.aid

	def setAID(self, newAID):
		self.aid = newAID
	
class YouTubeCmd(object):
    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.params = {}
        if kwargs is not None:
            for key,value in kwargs.items():
                self.params[key] = value
    def create_dict(self, prefix, **kwargs):
        tmp_dict = { "{prefix}_sc".format(prefix=prefix) : self.cmd }
        pprint.pprint(self.params)
        for key in self.params.keys():
            tmp_dict["{prefix}{name}".format(prefix=prefix, name=key)] = self.params[key]
        if self.cmd == "setPlaylist":
            tmp_dict["{prefix}{name}".format(prefix=prefix, name="listId")] = kwargs["listId"]
        return tmp_dict 
       

class YouTubeRemote(object):
    token = ""
    sid = ""
    gsessionid = ""
    seq = 0
    screen_id = None

    hooks = {}
    def hook_S(self, cmd, params):
        self.session.setGsession(params[0])
    def hook_c(self, cmd, params):
        self.session.setSid(params[0])

    def hook_playlistModified(self,cmd,params):
        self.listId = params[0]["listId"] 
        pprint.pprint(params)

    hooks["playlistModified"] = hook_playlistModified
    hooks["S"] = hook_S
    hooks["c"] = hook_c
       

    def __init__(self):
        self.screen_id = None
        self.uuid = uuid.uuid4()
        self.sid = ""
        self.aid = -1
        self.rid = RID()
        self.session = YouTubeLoungeSession()
        self.ofs = 0
        self.listId = None
    
    def loadConfig(self, fd):
        data = json.load(fd)
        self.screen = data["screen"]
        self.controler = data["controler"]

    def loadLoungeToken(self):
        r = requests.post("https://www.youtube.com/api/lounge/pairing/get_lounge_token_batch",
            data = {'screen_ids' : self.getScreenId()})
        data = json.loads(r.text)
        pprint.pprint(data)
        self.screen_id = data['screens'][0]['screenId']
        self.loungeToken = data['screens'][0]['loungeToken']
        self.expiration = data['screens'][0]["expiration"]

    def doOpenChannel(self, initial):
        resp = None
        url_str = None
        url_params = {}
        url_data = {}
        url_str = "https://www.youtube.com/api/lounge/bc/bind"
        url_params["device"] = "REMOTE_CONTROL"
        url_params["mdx-version"] = 3 
        url_params["ui"] = 1 
        url_params["v"] = 2 
        url_params["name"] = "Desktop"
        url_params['app'] = 'youtube-desktop'
        url_params["loungeIdToken"] = self.screen["loungeToken"]
        url_params["id"] = str(self.uuid)
        url_params["VER"] = 8
        url_params["CVER"] = 1
        url_params["zx"] = zx() 
        if initial == True:
            url_params["RID"] = self.rid.Next()
            
        if initial == True:
            url_data["count"] = 0
            r = requests.post(url_str, params = url_params, data = url_data)
            index = 0
            while index < len(r.text):
                index_prim = r.text.find('\n', index);
                response_len = int(r.text[index:index_prim])
                j = json.loads(r.text[index_prim+1:index_prim+1+response_len])
                self.doParseResponseMessages(j)
                index = index_prim+1+response_len;
        return None

    def doParseResponseMessages(self, messages):
        for idx, msg in messages:
            self.doParseOneMessage(msg[0], msg[1:])

    def doParseOneMessage(self, msg, params):
        if msg in self.hooks:
            self.hooks[msg](self=self,cmd=msg, params=params)
        else:
            print("No hook {msg}".format(msg=msg))
            pprint.pprint(params)


    def doBind(self):
        resp = self.doOpenChannel(True)
        #for _,i in resp:
        #    self.doParseRawMessage(i)

    def doConnect(self):
        self.loadLoungeToken()
        self.doBind()
 
    def doPairCode(self, pairCode):
        self.pairCode = pairCode

    def doPairOld(self):
        r = requests.post("https://www.youtube.com/api/lounge/pairing/register_pairing_code",
                data = { 'pairing_code':"038145835624", "screenId" : self.getScreenId() })
        print(r.text)

    def getScreenId(self):
        if self.screen_id == None:
            r = requests.get('https://www.youtube.com/api/lounge/pairing/generate_screen_id')
            print(r.text)
            self.screen_id = r.text
        return self.screen_id

    def doPair(self):

        r = requests.post("https://www.youtube.com/api/lounge/pairing/get_screen",
                data={'pairing_code': self.pairCode })
        if r.status_code == 200:
            data = json.loads(r.text)
            pprint.pprint(data)
            return True
        return False

    def getLoungeOnline(self):
        data = { "lounge_token" : self.screen["loungeToken"] }
        r = requests.post('https://www.youtube.com/api/lounge/pairing/get_screen_availability', data=data)
        pprint.pprint(r.text)
   

    def load_token(self, data):
        self.token = data['screen']['loungeToken']

    def connect(self):
        r = requests.get('http://www.youtube.com/api/lounge/bc/test?VER=8&TYPE=xmlhttp')

        data = self._send('http://www.youtube.com/api/lounge/bc/bind?RID=1&VER=8&CVER=1&id={remote_id}&device=REMOTE_CONTROL&app={remote_app}&name={remote_name}'.\
                format(remote_id=self.remote_id, remote_app=self.remote_app,
                    remote_name=urllib.parse.quote(self.remote_name)))
        self.sid = data[0][1][1]
        self.gsessionid = data[1][1][1]

    def _send(self, url, data=None):
        r = requests.post(url, data=data, headers={
            'X-YouTube-LoungeId-Token': self.token,
            'User-Agent': "YouTubeRemote",
            })
        data = "\n".join(r.text.splitlines()[1:])
        data = json.loads(data)
        return data


    def doUpdateStatus(self):
        if self.session.sid == None:
            self.doOpenChannel(True)
        url_address = "https://www.youtube.com/api/lounge/bc/bind"
        url_params = {}
        url_params["device"] = "REMOTE_CONTROL"
        url_params['app'] = 'youtube-desktop'
        url_params["name"] = "Desktop"
        url_params["loungeIdToken"] = self.screen["loungeToken"]
        url_params["id"] = str(self.uuid)
        url_params["VER"] = 8
        url_params["zx"] = zx() 
        url_params["SID"] = self.session.sid
        url_params["RID"] = "rpc"
        url_params["AID"] = self.session.getAID();
        url_params["TYPE"] = 'xmlhttp'
        url_params["CI"] = 0
        url_params['mdx-version']=3
        url_params['v']=2

        url_params["gsessionid"] = self.session.gsession
        pprint.pprint(url_params)

        r = requests.get(url_address, params = url_params)
        print(r.text[:20])


    def doCmd(self, cmds):
        if self.session.sid == None:
            self.doOpenChannel(True)

        tmp_cmds = cmds
        if isinstance(cmds ,YouTubeCmd):
            tmp_cmds = [ cmds ]

        cmd_array = {"count" : len(cmds), "ofs" : self.session.getOfs() }

        for idx,i in enumerate(tmp_cmds):
            prefix = "req{idx}_".format(idx=idx)
            print(prefix)
            cmd_array.update(i.create_dict("req{idx}_".format(idx=idx), listId = self.listId))
        
        url_address = "https://www.youtube.com/api/lounge/bc/bind"
        url_params = {}
        url_params["device"] = "REMOTE_CONTROL"
        url_params["name"] = "Desktop"
        url_params["loungeIdToken"] = self.screen["loungeToken"]
        url_params["id"] = str(self.uuid)
        url_params["VER"] = 8
        url_params["zx"] = zx() 
        url_params["SID"] = self.session.sid
        url_params["RID"] = self.rid.Next()
        url_params["AID"] = self.session.getAID();
        url_params["gsessionid"] = self.session.gsession
        pprint.pprint(url_params)
        pprint.pprint(cmd_array)
        r = requests.post(url_address, params = url_params, data = cmd_array)
        pprint.pprint(r.text)
        

        
    def do(self, data):
        apidata = {
            'count': 1,
        }

        for k, v in data.items():
            apidata['req{0}_{1}'.format(self.seq, k)] = v

        #self.rid += 1
        
        result = self._send("http://www.youtube.com/api/lounge/bc/bind?RID={rid}&SID={sid}&VER=8&CVER=1&gsessionid={gsessionid}".\
                format(sid=self.sid, gsessionid=self.gsessionid, rid=self.rid),
                data=apidata)
        self.seq += 1

        return result

    def queue(self, video_id):
        self.do({
            '_sc': 'addVideo',
            'videoId': video_id,
        })

    def set(self, video_id):
        self.queue(video_id)
        self.do({
            '_sc': 'setVideo',
            'currentTime': 0,
            'videoId': video_id,
        })

    def play(self):
        self.do({'_sc': 'play'})

    def pause(self):
        self.do({'_sc': 'pause'})


def get_videoid(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == 'youtu.be':
        return path.lstrip('/')
    elif parsed.netloc.endswith('youtube.com'):
        qs = urllib.parse.parse_qs(parsed.query)
        if 'v' in qs:
            return qs['v'][0]
        else:
            parts = parsed.path.split('/')
            return parts[-1]
    else:
        return url


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
            description="Command-line YouTube Leanback remote")
    parser.add_argument('--code', help="Code")
    parser.add_argument('--video', help="Play video")
    parser.add_argument('--queue', help="Queue video")
    parser.add_argument('--next', help="Next video")
    parser.add_argument('--prev', help="Prev")
    parser.add_argument('--play_id', help="Play entry")
    parser.add_argument('--volume', help="Volume")
    args = parser.parse_args()


    remote = YouTubeRemote()
    
    if not args.code == None:
      pass
    #remote.doPairCode(args.code)
    #remote.getScreenId()
    #remote.doPair();
    #remote.doConnect()
    #remote.loadLoungeToken()
    #remote.doPair()

    remote.loadConfig(open("config.json"))
    #remote.getLoungeOnline()
    #remote.doBind()
    #remote.doCmd([YouTubeCmd(cmd="play"), YouTubeCmd(cmd="pause")])

    if args.volume != None:
        remote.doCmd([YouTubeCmd(cmd="setVolume", volume = args.volume, muted = 'false')])
    #remote.doUpdateStatus()
    #sys.exit(0)
    if args.video != None:
        remote.doCmd([YouTubeCmd(cmd="setVideo", currentTime=0, videoId=args.video)])
    elif args.queue != None:
        remote.doCmd([YouTubeCmd(cmd="addVideo", videoId = args.queue)]) 
    elif args.play_id != None:
        remote.doCmd([YouTubeCmd(cmd="setPlaylist", currentIndex = args.play_id, currentTime = 0)]) 

