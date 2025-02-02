# This software includes Flask, which is licensed under the BSD-3-Clause License.
# Copyright (c) 2010 Pallets
# See the LICENSE file for more details.

from flask import Flask, render_template, request, redirect, send_file, session

import json
import socket
import random
import uuid
import random
import string
import datetime
import html
import re

app = Flask(__name__)
app.secret_key = "Secrets!"

def render(text):
    text = re.sub(r"&gt;&gt;([0-9]+)", r"<a href='#r\1'>&gt;&gt;\1</a>", text)    
    text = re.sub(r"!Img:&quot;(.+)&quot;", r"<img src='\1'>", text)    
    text = re.sub(r"!Video:&quot;(.+)&quot;", r"<video src='\1'>", text)    
    text = re.sub(r"!URL:&quot;(.+)&quot;", r"<a href='\1'>\1</a>", text)    
    text = re.sub(r"!IFR:&quot;(.+)&quot;", r"<iframe src='\1'></iframe>", text)    
    


    if session.get("ngword") is not None:
        for i in session.get("ngword", "").split():
            if i in text:
                text = "<b style='color:red'>【NGワードが含まれています】</b>"
                break

    text = text.replace("\n","<br>")
    return text


def get_addr_from_instance_id(instance_id: str):
    servers = open("servers.txt","r").read().split("\n")

    for line in servers:
        
        id_, addr = line.split()
        
        if instance_id == id_:
            return addr


def is_mobile(ua):
    mobile_pattern = re.compile(r"Mobile|Android|iPhone|iPad|iPod", re.IGNORECASE)
    return bool(mobile_pattern.search(ua))


def id_gen():
    c = "".join(random.Random(f"{request.headers.get("X-Forwarded-For","")} Z19 TwineViewer {datetime.datetime.now().strftime('%Y/%m/%d')}").choices(string.ascii_letters+string.digits, k=4))
    
    if is_mobile(request.user_agent.string):
        return "V:"+c
    else:
        return "V-"+c



@app.route("/ifconfig")
def ifconfig():
    return request.headers.get("X-Forwarded-For", "???")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/setting", methods=["GET","POST"])
def setting():
    if request.method == "POST":
        session["ngword"] = request.form.get("ngword", "")
        session["hide_id"] = request.form.get("hide_id","off")
        session["hide_name"] = request.form.get("hide_name","off")
        
    return render_template("setting.html", ngword=session.get("ngword", ""),
                           hide_id=(session.get("hide_id", "off") == "on"),
                           hide_name=(session.get("hide_name", "off") == "on"))


@app.route("/<instance_id>/")
def bbs(instance_id):
    
    if instance_id == "favicon.ico":
        return send_file("./static/favicon.ico")
    
    addr = get_addr_from_instance_id(instance_id)
    
    if addr is not None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((addr.split("-")[0], int(addr.split("-")[1])))
        s.send(b"getall<END>")
        
        buff = ""
        while True:
            c = s.recv(1024)
            if c == b"":
                break
            buff += c.decode(errors="ignore")
        
        s.close()
        
        c = json.loads(buff)
        
        return render_template("bbs.html", title=c.get("title", "UNTITLE"), description=c.get("description","???"), threads=c.get("threads",[]), instance_id=instance_id)
        
    else:
        return "インスタンスが登録されていません"   
    

@app.route("/<instance_id>/mkthr", methods=["POST"])
def makenewthread(instance_id):
    addr = get_addr_from_instance_id(instance_id)
    
    if addr is not None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((addr.split("-")[0], int(addr.split("-")[1])))
        
        data = {
            "title": html.escape(request.form.get("title")).replace("<END>","")[0:30],
            "thrid": str(uuid.uuid4()),
            "contents": [
                {
                    "name": html.escape(request.form.get("name")).replace("<END>",""),
                    "text": html.escape(request.form.get("text")).replace("<END>",""),
                    "id": id_gen(),
                    "timestamp": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                }
            ]
        }
        if data["contents"][0]["name"] == "":
            data["contents"][0]["name"] = "名無し"
        
        if data["title"] != "" and data["contents"][0]["text"] != "":
            
            s.send(f"makethr{json.dumps(data, ensure_ascii=False)}<END>".encode())
            
            s.close()
        
            return redirect(f"/{instance_id}/thread/{data['thrid']}")
        else:
            return "エラー"
    else:
        return "インスタンスが登録されていません"   
    

@app.route("/<instance_id>/thread/<thrid>", methods=["GET"])
def viewthread(instance_id, thrid):
    addr = get_addr_from_instance_id(instance_id)
    
    if addr is not None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((addr.split("-")[0], int(addr.split("-")[1])))
        
        thrid = thrid.replace("<END>","")
        
        s.send(f"get-thr{thrid}<END>".encode())
        buf = ""
        while True:
            a = s.recv(1024)
            buf+=a.decode(errors="ignore").replace("<END>","")
            if "<END>" in a.decode(errors="ignore"):
                break
        s.close()
        
        thread = json.loads(buf)
        return render_template("thread.html", thread=thread, 
                               instance_id=instance_id, render=render,
                               hide_id = session.get("hide_id") == "on",
                               hide_name = session.get("hide_name", "off") == "on")
            
    else:
        return "インスタンスが登録されていません"   

@app.route("/<instance_id>/mkrsp/<thrid>", methods=["POST"])
def makethrrsp(instance_id, thrid):
    addr = get_addr_from_instance_id(instance_id)
    
    if addr is not None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((addr.split("-")[0], int(addr.split("-")[1])))
        
        thrid = thrid.replace("<END>","")
        data = {
            "thrid": thrid,
            "data": {
                "name": html.escape(request.form.get("name")).replace("<END>",""),
                "text": html.escape(request.form.get("text")).replace("<END>",""),
                "id": id_gen(),
                "timestamp": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            }
        }
        
        if data["data"]["name"] == "":
            data["data"]["name"] = "名無し"
        
        
        if data["data"]["text"] != "":
            s.send(("postthr"+json.dumps(data, ensure_ascii=False)+"<END>").encode())
            s.close()
            
        
        return redirect(f"/{instance_id}/thread/{thrid}")
            
    else:
        return "インスタンスが登録されていません"   

@app.route("/<instance_id>/poll/<thrid>")
def poll(instance_id, thrid):
    addr = get_addr_from_instance_id(instance_id)
    
    if addr is not None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((addr.split("-")[0], int(addr.split("-")[1])))
        
        thrid = thrid.replace("<END>","")
        
        s.send(f"pollthr{thrid}<END>".encode())
        buf = ""
        while True:
            a = s.recv(1024)
            buf+=a.decode(errors="ignore").replace("<END>","")
            if "<END>" in a.decode(errors="ignore"):
                break
        s.close()
        
        thread = json.loads(buf)
        
        thread["contents"][-1]["index"] = len(thread["contents"])
        thread["contents"][-1]["text"] = render(thread["contents"][-1]["text"])
        
        if session.get("hide_name", "off") == "on":
            thread["contents"][-1]["name"] = "名無し"
        
        return thread["contents"][-1]
            
    else:
        return "インスタンスが登録されていません"   



app.run("localhost", 31415, True)
