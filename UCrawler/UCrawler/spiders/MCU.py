from bs4 import BeautifulSoup
from selenium import webdriver
import scrapy
import re
import json
from scrapy.http import FormRequest
import urllib
from UCrawler.items import UcrawlerItem

def innerHTML(element):
        return element.decode_contents(formatter="html")
class McuSpider(scrapy.Spider):
    name = 'MCU'
    start_urls =["http://www.mcu.edu.tw/student/new-query/sel-query/qslist.asp"]
    deptRefNodeDict = {}
    schoolPlace ={}
    result ={}
    chineseNum =['一','二','三','四','五','六','七']
    chineseKey ='研'
    def start_requests(self):
        #先用selenium模仿web使用者動作
        # driver=webdriver.Chrome(executable_path="./chromedriver")
        driver = cross_selenium(True)
        
        driver.get(self.start_urls[0])
        #一些仿USER的動作
        #放入bs4裏面
        #.decode('big5', 'ignore')
        soupsch = BeautifulSoup(driver.page_source, "html.parser")
        #取得所有系所列表
        deptRefNodeList = [ re.sub(r"\r|\n|\t|[ ]","",innerHTML(x)) for x in soupsch.find('select',{'name':'dept1'}).find_all('option')]
        for x in deptRefNodeList:
            if x.find('-')!=-1:
                node =x.split('-')
                self.deptRefNodeDict[node[0]] =node[1]
        #End 取得所有系所列表
        #取得所有校區列表
        contents = [str(x['value']) for x in soupsch.find('select',{'name':'sch'}).find_all('option')]
        self.schoolPlace ={str(x['value']):innerHTML(x).replace('&nbsp;','').strip() for x in soupsch.find('select',{'name':'sch'}).find_all('option')}
        for i in contents :
            if i == '' :
                continue
            else:
                schbody ={'sch' : i }#urllib.parse.urlencode(schbody)
                schheaders={'Content-type': 'application/x-www-form-urlencoded'}
                #yield scrapy.http.FormRequest("http://www.mcu.edu.tw/student/new-query/sel-query/qslist_1.asp", callback=self.parse_detail, formdata=schbody)
                yield scrapy.http.Request("http://www.mcu.edu.tw/student/new-query/sel-query/qslist_1.asp",method ="POST",body=urllib.parse.urlencode(schbody).encode('utf-8'),headers=schheaders,callback=self.parse)
    
    def parse(self,response):
        soupSimpleData =BeautifulSoup(response.body.decode(response._body_declared_encoding(), 'ignore'), "html.parser")
        if len(soupSimpleData.find_all('tr'))==0:
            return
        soupSimpleDataRow =soupSimpleData.find('table').find_all('tr')
        for tr in range(len(soupSimpleDataRow)):
            if tr == 0 :
               continue
            classdict=UcrawlerItem()
            col =soupSimpleDataRow[tr].find_all('td')
            #抓取課程名稱
            IDClass =innerHTML(col[2].find_all('font')[0]).replace('&nbsp;','').split(' ')
            #上課的系所年級Class
            if len(IDClass)!=1 is not None:
                classdict['class']=IDClass[1]
            else:
                classdict['class']=None
            #classdict['class']=IDClass[0]
            #innerHTML(col[2].find_all('font')[0]).replace('&nbsp;','').split(' ')[0]
            #抓取課程編號
            #IDCode =innerHTML(col[1].find_all('font')[0]).split(' ')[0].replace('&nbsp;','')
            classdict['code']=innerHTML(col[1].find_all('font')[0]).split(' ')[0].replace('&nbsp;','')
            #學分
            classdict['credits']=innerHTML(col[9].find_all('font')[0])
            #print(ID[0:2])
            
            #開課給哪個系
            for_dept =''
            for_grade =''
            
            if classdict['class'] is not None:
                if classdict['class'].find(self.chineseKey) != -1:
                    for_dept =classdict['class'][0:classdict['class'].find(self.chineseKey)]
                    for_grade =classdict['class'][classdict['class'].find(self.chineseKey):len(classdict['class'])]
                else:
                    for i in range(len(self.chineseNum)) :
                        if classdict['class'].find(self.chineseNum[i]) != -1:
                            for_dept =classdict['class'][0:classdict['class'].find(self.chineseNum[i])]
                            for_grade =classdict['class'][classdict['class'].find(self.chineseNum[i]):len(classdict['class'])]
            classdict['for_dept'] =for_dept
            classdict['grade']= for_grade
            #開課單位
            if self.deptRefNodeDict.get(IDClass[0][0:2]) is not None:
                classdict['department']=self.deptRefNodeDict[IDClass[0][0:2]]
            else:
                classdict['department']=None
            #上課地點
            classdict['location']=innerHTML(col[7].find_all('font')[0]).replace('&nbsp;','').strip().split('<br/>')
            #classdict['obligatory_tf'] =innerHTML(col[8].find_all('font')[0])
            #是否必修
            if innerHTML(col[8].find_all('font')[0]) == '必修' :
                classdict['obligatory_tf'] = True
            else:
                classdict['obligatory_tf'] = False
            #切時間
            timeArr =[]
            timelist =innerHTML(col[5].find_all('font')[0]).replace('&nbsp;','').split('<br/>')
                #print(range(len(timelist)))
            for i in range(len(timelist)):
                    #最後一航不用看
                if i!=len(timelist)-1:
                    tmp =timelist[i].split(':')
                    timeDict ={}
                    timeDict['day']=tmp[0].replace('星期','').strip()
                    Sessions =tmp[1].replace('節','').strip().split(' ')
                    SessionArr =[]
                    for j in range(len(Sessions)):
                        if Sessions[j]!='':
                            SessionArr.append(Sessions[j])
                    timeDict['time']=SessionArr
                    timeArr.append(timeDict)
                else :
                    print(i)
            classdict['time']=timeArr
            classdict['title']=innerHTML(col[1].find_all('font')[0]).split(' ')[1].replace('&nbsp;','')
            classdict['note']=innerHTML(col[13].find_all('font')[0]).replace('&nbsp;','').strip()
            classdict['professor']=innerHTML(col[4].find_all('a')[0].find_all('font')[0]).replace('&nbsp;','').replace('<br/>','、')
            #有些教授的欄位只有一個: 就需要用著個清空它
            if classdict['professor'].strip() ==':':
                classdict['professor'] =''
            #開課學校
            classdict['campus']='MCU'#+classdict['campus'][classdict['campus'].find('【'):len(classdict['campus'])]

            yield classdict