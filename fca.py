#!/usr/bin/python
# -*- coding: utf-8 -*-
# Name      : File Changes Analyzer
# Author    : wofeiwo#80sec.com
# Version   : 2.0
# Date      : 2010-2-1
# Updated   : 2013-3-12
# Changelog : 1. add ownerdiff, mysqlfile functions.

# 发现文件系统中的异常改动文件

import sys, os, string, re, getopt, pwd, fnmatch
from datetime import datetime, timedelta

def usage(program = sys.argv[0]):
    print "Usage %s [options]\n" % program
    print \
"""
  -a, --action=actionname               What to do(ctimegroup, ownerdiff, mysqlfile, default = all)
  -u, --user=owner                      Onwer name of the webpath files(default = current user)
  -m, --mysqluser=mysqluser             User name of the mysql(default = mysql)
  -e, --ext=php,asp,jsp                 Filter the ext, only show these files(you can use 'all', default = 'php', 'jsp', 'asp', 'pl', 'py', 'aspx', 'cer', 'asa')
  -w, --webroot=webpath                 Real web root path
  -n, --number=filenumber               Files less than this number, display the them(default:5) (for ctimegroup)
  -t, --timedelta=time                  Time group (minutes, default = 5)
  -h, --help                            Display this help and exit
  
  example: %s -a ctimegroup -w /var/www -n 5 -t 10
  example: %s -a mysqlfile -w /var/www -m database
  example: %s -w /var/www # show all abnormal files """ % (program, program, program)

# 处理参数
def parseArgs(args):
    options = {}
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:m:e:n:t:w:a:", \
        ["help", "user=", "mysqluser=", "ext=", "number=", "timedelta=", "webroot=", "action="])
    except getopt.GetoptError, e:
        sys.stderr.write('[-] %s\n' % str(e))
        usage(sys.argv[0])
        sys.exit(2)
        
    for o, v in opts:
        # print(o, v)
        if o in ["-a", "--action"]:
            options['action'] = str(v)

        elif o in ["-n", "--number"]:
            options['number'] = int(v)
            
        elif o in ["-t", "--timedelta"]:
            options['timedelta'] = int(v)
    
        elif o in ["-u", "--user"]:
            options['user'] = str(v)
    
        elif o in ["-m", "--mysqluser"]:
            options['mysqluser'] = str(v)
    
        elif o in ["-e", "--ext"]:
            if str(v).strip() == 'all':
                options['ext'] = [''] # will be *.*
            else:
                options['ext'] = [ str(s).strip() for s in v.split(',') ] # convert to list

        elif o in ["-w", "--webroot"]:
            options['webroot'] = os.path.realpath(str(v))

        elif o in ["-h", "--help"]:
            usage(sys.argv[0])
            sys.exit()
            
    # 设置一些默认值
    
    if not options.has_key('webroot'):
        usage(sys.argv[0])
        sys.exit(2)
    
    if not options.has_key('action'):
        options['action'] = 'all' 
        
    if options['action'] not in ['all', 'ctimegroup', 'mysqlfile', 'ownerdiff']:
        options['action'] = 'all'
        sys.stderr.write('[-] No such action, action will set to \'all\'.\n')
        
    if not options.has_key('number'):
        options['number'] = 5
    
    if not options.has_key('timedelta'):
        options['timedelta'] = 5
        
    if not options.has_key('user'):
        options['user'] = pwd.getpwuid(os.getuid())[0] # 当前用户

    if not options.has_key('mysqluser'):
        options['mysqluser'] = 'mysql'

    if not options.has_key('ext'):
        options['ext'] = ['php', 'jsp', 'asp', 'pl', 'py', 'aspx', 'cer', 'asa']

    return options


def getStats(path):
    stats = []
    for root, dirs, names in os.walk(path):
        for f in names:
            filepath = os.path.join(root, f)
            stat = os.lstat(filepath)
            stats.append({
                'path' : filepath,
                'stat' : stat
            })
    return stats

def ctimegroup(stats, dtime, fnum): # 按照ctime分组
    fsDict = {} # 所有文件ctime信息
    tmp = {} # 时间区段分组，key = 时间区段， value = [ file1, file2 ]

    for f in stats:
        filepath = f['path']
        stat = f['stat']
        ctime = datetime.fromtimestamp(stat.st_ctime)            
        fsDict[filepath] = ctime
         
    flag = False

    for i in fsDict.items():
        for k in tmp.keys():
            flag = False
            if (i[1] - k >= timedelta(minutes = -dtime)) and (i[1] - k <= timedelta(minutes = dtime)): # 不超过时间限制
                tmp[k].append(i[0]) # 加入文件路径
                flag = True
                break
        if not flag:
            tmp[i[1]] = [i[0]] # 新的时间区段

    # 按照时间区段排序下
    a = tmp.keys()
    a.sort()

    for k in a:
        print "TimeDelta:", k.isoformat()[:16], "(正负%d分钟)" % dtime
        print "Files: "
        if len(tmp[k])>fnum:
            print "%d items." % len(tmp[k])
        else:
            for v in tmp[k]:
                print v
        print '--------------------------------------------------------------------------------------------------------'
def ownerdiff(stats, owner, ext): # 区分不同属主文件
    result = []
    for f in stats:
        filepath = f['path']
        stat = f['stat']
        fileowner = pwd.getpwuid(stat.st_uid)[0]
        if fileowner != owner:
            for e in ext:
                if fnmatch.fnmatch(filepath, '*.' + e + '*'):
                    result.append({
                        'path'   : filepath,
                        'stat'   : stat,
                        'reason' : 'Onwer is different'
                    })

    return result

def mysqlfile(stats, mysqluser, ext): # 显示mysql创建的文件。
    result = []
    for f in stats:
        filepath = f['path']
        stat = f['stat']
        fileowner = pwd.getpwuid(stat.st_uid)[0]
        filemode  = oct(stat.st_mode)[-3:]
        if fileowner == mysqluser or filemode == '666': # mysql属主，或者属性666.MySQL在源代码中写死了导出的文件权限为666.
            for e in ext:
                if fnmatch.fnmatch(filepath, '*.' + e + '*'):
                    result.append({
                        'path'   : filepath,
                        'stat'   : stat,
                        'reason' : 'Maybe MySQL outfile'
                    })

    return result

def printResult(results):
    print 'File Changes Analyzer Result:'
    print '--------------------------------------------------------------------------------------------------------'
    print '%-60s | %-20s | %-15s | %-20s' % ('filepath', 'reason', 'owner', 'ctime')
    print '--------------------------------------------------------------------------------------------------------'
    for r in results:
        print '%-60s | %-20s | %-15s | %-20s'% ( r['path'], r['reason'], pwd.getpwuid(r['stat'].st_uid)[0], datetime.fromtimestamp(r['stat'].st_ctime))  
    print '--------------------------------------------------------------------------------------------------------'

def main():    
    options = parseArgs(sys.argv)
    stats = getStats(options['webroot'])

    # 根据action做不同的事情
    
    if options['action'] == 'ctimegroup':
        ctimegroup(stats, options['timedelta'], options['number'])
    elif options['action'] == 'ownerdiff':
        results = ownerdiff(stats, options['user'], options['ext'])
    elif options['action'] == 'mysqlfile':
        results = mysqlfile(stats, options['mysqluser'], options['ext'])
    else:
        results = ownerdiff(stats, options['user'], options['ext'])
        results += mysqlfile(stats, options['mysqluser'], options['ext'])
        ctimegroup(stats, options['timedelta'], options['number'])

    printResult(results)

if __name__ == '__main__':
    main()
