from db import *
import random
from operator import itemgetter

def get_min():
    conn, cur = connection()
    cur.execute('SELECT minimum FROM jobs')
    draws = cur.fetchall()
    count = 0
    for i in range(len(draws)):
        count += draws[i]['minimum']
    return count

def get_available():
    conn, cur = connection()
    cur.execute('SELECT COUNT(*) FROM here')
    people = cur.fetchall()
    peoplenum = people[0]['COUNT(*)']
    return peoplenum

def get_job_total():
    conn, cur = connection()
    cur.execute('SELECT job_total FROM here')
    ids = cur.fetchall()
    total = 0
    for i in range(len(ids)):
        total += ids[i]['job_total']
    conn.close()
    return total

def high_low():
    start = 0
    conn, cur = connection()
    cur.execute('SELECT job_total, id FROM here')
    ids = cur.fetchall()
    for i in range(len(ids)):
        low = start
        high = start + ids[i]['job_total']
        start = high
        ids[i]['low'] = low
        ids[i]['high'] = high
    conn.close()
    return ids

def choose_people():
    rangeDict = high_low()
    #print(len(rangeDict))
    rangeList = list(high_low())
    total = get_job_total()
    print('Total is ' + str(total))
    count = get_min()
    idList = []
    start = 0

    '''
    * I cant change the variable in range function when a for loop happens. If no Break, it breaks loop because pop happened
    * sometimes it is not found in list
    '''


    for i in range(count):
        randnum = random.randint(1, total)
        # print(randnum)
        # found = False
        for j in range(len(rangeList)):
            if randnum > rangeList[j]['low'] and randnum <= rangeList[j]['high']:
                idList.append([rangeList[j]['id'], rangeList[j]['job_total']])
                total -= rangeList[j]['job_total']
                # print('FOUND ' + str(rangeList[j]['id']))
                #print(total)
                rangeList.pop(j)
                # found = True
                break
        # if not found:
        #     print('not found!!!')
        #     print(rangeList)
        #     print('TOTAL IS ' + str(total))
        # found = False



        for k in range(len(rangeList)):
            low = start
            high = start + rangeList[k]['job_total']
            start = high
            rangeList[k]['low'] = low
            rangeList[k]['high'] = high
        #print(rangeList)
        start = 0

    idList.sort(key=itemgetter(1), reverse=True)

    conn, cur = connection()
    cur.execute('SELECT name, difficulty, minimum, id FROM jobs WHERE dump = 1')
    job = cur.fetchall()
    jobName = job[0]['name']
    jobAmount = job[0]['difficulty']
    jobId = job[0]['id']
    for p in range(len(rangeDict)):
        found = False
        for q in range(len(idList)):
            if rangeDict[p]['id'] == idList[q][0]:
                found = True
        idnum = rangeDict[p]['id']
        if not found:
            cur.execute('INSERT IGNORE INTO jobs_done(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (idnum, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('INSERT INTO jobs_done_history(id, job_name, job_id, amount) VALUES(%s, %s, %s, %s)', (idnum, jobName, jobId, jobAmount))
            conn.commit()
            cur.execute('UPDATE swimmers set job_total = job_total + %s WHERE id=%s', (int(jobAmount), idnum))
            conn.commit()
    conn.close()

    return idList
