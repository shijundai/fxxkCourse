#coding:utf-8
import requests
import io,os,re
import ConfigParser
import codecs
import time

saveDirectory=None
imageWidth=None

def readConfig():
    global saveDirectory,imageWidth;
    #cf = ConfigParser.ConfigParser()
    cf = ConfigParser.SafeConfigParser()
    with codecs.open('conf.ini', 'r', encoding='utf-8') as f:
        cf.readfp(f)

    #cf.read("conf.ini",encoding="utf-8-sig")
    saveDirectory=cf.get("conf","saveDirectory")
    imageWidth=cf.get("conf","imageWidth")
    print(u"下载保存路径为："+saveDirectory)
    print(u"下载图片宽段为："+imageWidth)

#文件夹是否存在 不存在则新建
def createDir(path):
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path);

#写文本文件
def writeTextFile(path,fileName,text,writeModel="w"):
    createDir(path)
    if writeModel=="w" and os.path.exists(path + "\\" + fileName) == False:
        f=file(path+"\\"+fileName,writeModel)
        f.write((text+"\r\n").encode('utf-8'));

#写二进制文件
def writeBinaryFile(path,fileName,content):
    createDir(path)
    with open(path+"\\"+fileName, 'wb') as f:
        f.write(content)

#登录状态监测
def check_login(imageId=None,s=None):
    print("登录检测中....")
    statusCheckUrl = 'https://www.fxiaoke.com/FHH/EM0HXUL/Authorize/GetQRImageStatus';
    data={"{\"ImageID\":\""+imageId+"\"}":""}
    r = s.post(statusCheckUrl, data=data).json()
    if r['Value']['Status']==2:
        print("登录二维码已失效，请重新启动")
        os._exit();
    return r['Value']['Status']!=1;

#打开登录二维码
def openQrImage():
    imageInfoUrl = "https://www.fxiaoke.com/FHH/EM0HXUL/Authorize/GetQRImage"
    picDir = "QR.png"
    qrImageUrl = "https://www.fxiaoke.com/FSC/N/QRLogin/GetQRImage?QRCode="
    imgInfoRes = requests.post(url=imageInfoUrl, json={})
    qrImgInfo = imgInfoRes.json()
    imageId = qrImgInfo['Value']['ImageID']
    qrSeq = qrImgInfo['Value']['QRCode']
    s = requests.session()
    with open(picDir, 'wb') as f:
        f.write(s.get(qrImageUrl + qrSeq).content)
        os.startfile(picDir);
    return s,imageId;

#登陆
def login():
    s,imageId=openQrImage()
    isNotLogin = True;
    print("请扫描二维码登录")
    while isNotLogin:
        isNotLogin = check_login(imageId=imageId,s=s);
    downAndSaveAllCourses(s);

#从登录后的首页获取公司id、用户id、fs_token
def getTraceAndToken(s):
    indexUrl = "https://www.fxiaoke.com/XV/Home/Index"
    indexText = s.get(indexUrl).text;
    fsToken = re.search(r"value=\"(\w+)\"\s+id=\"fs_token\"", indexText).groups()[0]
    enterpriseAccount = re.search(r"\"enterpriseAccount\":\"(\w+)\"", indexText).groups()[0]
    employeeID = re.search("\"employeeID\":(\d+)", indexText).groups()[0]
    #45678901是随便加的 这个参数没找到规律及意义 貌似是为了避免浏览器缓存产生的随机数
    traceId = "E-E." + enterpriseAccount + "." + employeeID + "-" + "45678901";
    print("fs_token:"+fsToken+"\tenterpriseAccount:"+enterpriseAccount+"\temployeeID:"+employeeID)
    return traceId,fsToken

#获取课程列表
def getCourseList(s,traceId,fsToken,pageSize,pageNo):
    courseListUrl = "https://www.fxiaoke.com/FHH/EM1HFsTrain/course/list?traceId="+traceId+"&_fs_token="+fsToken
    return s.post(courseListUrl,json={"channelId": -1, "pageNo": pageNo, "pageSize": pageSize, "orderBy": 2, "trainingAccess": 0}).json()['Value']['data']['result']

#下载课程
def downCourse(s,c,learnUrl):
    #封面图片url
    cid, cover = c['id'], c['cover'];
    posJson = {"id": cid, "trainingAccess": 0};
    res = s.post(learnUrl, json=posJson)
    resJs = res.json()
    #有关纷享逍客的培训不下载
    if resJs['Value']['data']['lecturers'][0]['name'].__contains__(u"会用纷享") == True:
        return;
    coverImgUrl = "https://www.fxiaoke.com/FSC/EM/File/GetByPath?path="
    savepath = saveDirectory + "\\" + c['name'].strip();
    writeTextFile(savepath, "profile.txt", resJs['Value']['data']['profile'])
    writeBinaryFile(savepath, "index.jpg",s.get(coverImgUrl + cover).content)
    for w in res.json()['Value']['data']['coursewares']:
        name="";
        if len(res.json()['Value']['data']['coursewares'])>1:
            name =  "\\"+w['name'].strip();
        docpath = None;
        if w.has_key('path') and w['path']!="":
            docpath=w['path'];
        elif w.has_key('hdURL'):
            docpath=w['hdURL']
        print(u"正在下载:" + docpath)
        if docpath.__contains__("https:")==False and docpath.__contains__("http:")==False :
            #文件页码
            pageCount = s.get("https://www.fxiaoke.com/dps/preview/DocPreviewByPath?path=" + docpath).json()['PageCount']
            #print("页码："+ str(pageCount))
            for pIndex in range(pageCount):
                #time.sleep(0.5)
                #获取大图片 适配电脑
                picUlr = "https://www.fxiaoke.com/dps/preview/DocPageByPath?path=" + docpath + "&pageIndex=" + str(pIndex) + "&width="+str(imageWidth)+"&maxContentLength=0";
                fileName = str(pIndex) + ".jpg";
                if os.path.exists(savepath+name + "\\" + fileName) == False:
                    try:
                        writeBinaryFile(savepath+name, fileName, s.get(picUlr).content)
                    except:
                        writeBinaryFile(savepath+name, str(pIndex) + ".jpg", s.get(picUlr).content)
        #如果是视频
        elif docpath.__contains__(".mp4")==True:
            fileName=w['name'] + ".mp4";
            if os.path.exists(savepath + "\\" + fileName) == False:
                writeBinaryFile(savepath,fileName,s.get(docpath).content);
        else:
            #如果是网页
            writeTextFile(savepath,"url.txt",docpath+"\r\n",writeModel="a+")

#下载所有课程
def downAndSaveAllCourses(s):
    print("登录成功，开始下载......")
    s.keep_alive = False;
    traceId, fsToken=getTraceAndToken(s)
    learnUrl = "https://www.fxiaoke.com/FHH/EM1HFsTrain/course/learn?traceId=" + traceId + "&_fs_token=" + fsToken
    startPageNo = 1;
    pageSize=9;
    courseList = getCourseList(s,traceId,fsToken,pageSize,startPageNo);
    downCount = (startPageNo-1)*pageSize;
    while len(courseList)!=0:
        for c in courseList:
            downCount += 1
            print(u"正在下载第：" + str(downCount)+u"条，"+c["name"])
            downCourse(s, c, learnUrl)
        startPageNo += 1;
        courseList = getCourseList(s, traceId, fsToken, pageSize, startPageNo);

#登录并下载所有课程
readConfig()
login()
