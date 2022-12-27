# -*- coding: utf-8 -*-
"""
Created on Fri Jun 10 19:40:30 2022

@author: breno.zipoli
"""
import psycopg2
import random
import requests

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres")
cur = conn.cursor()

bookid = ['1','2','3','4','5','6','7']
booktypeid = ['1','2','3','4']
userid = ['1','2','3']

timestoadd = 1
rowstoadd = 1000
REGIDX = 0

def truncate_table():
    cur.execute('TRUNCATE TABLE public."Sales"')
    conn.commit()

def select_all():
    cur.execute('SELECT COUNT (*) FROM (select * from public."Sales") AS tab')
    conn.commit()
    totalrows = cur.fetchone()
    return (totalrows)

for i in range(0, timestoadd):
    cur.execute('SELECT MAX("SaleId") FROM public."Sales"')
    lastsaleid = cur.fetchone()[0] + 1
    # lastsaleid = 0
    print("initial saleid = " + str(lastsaleid))
    
    cur.execute('SELECT COUNT(*) FROM public."Sales"')
    totalrows = cur.fetchone()[0] + 1
    print("totalrows  = " + str(totalrows))
    
    sql = """INSERT INTO public."Sales"("SaleId", "BookId", "BookTypeId", "UserId", "Value", "EntryDateTime") VALUES (sample)"""
    sql = sql.replace('sample', str(lastsaleid) + ', ' + random.choice(bookid)+ ', ' + random.choice(booktypeid) + ', ' + random.choice(userid)+', ' + str(random.choice(range(20,200))) + ', ' + "CURRENT_DATE - INTERVAL " + "'" + str(REGIDX) +" day'")

    
    for i in range (0, rowstoadd):
        sql = sql + ", (sample)"
        sql = sql.replace('sample', str(lastsaleid) + ', ' + random.choice(bookid)+ ', ' + random.choice(booktypeid) + ', ' + random.choice(userid)+', ' + str(random.choice(range(20,200))) + ', ' + "CURRENT_DATE - INTERVAL " + "'" + str(REGIDX) +" day'")
        lastsaleid = lastsaleid + 1
        if(REGIDX >= 254):
            REGIDX = 0
        REGIDX = REGIDX + 1
        
    
    cur.execute(sql)
    conn.commit()
    
        