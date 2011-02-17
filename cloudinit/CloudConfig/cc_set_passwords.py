# vi: ts=4 expandtab
#
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Author: Scott Moser <scott.moser@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cloudinit.util as util
import subprocess
import sys
import random
import string

def handle(name,cfg,cloud,log,args):
    if len(args) != 0:
        # if run from command line, and give args, wipe the chpasswd['list']
        password = args[0]
        if 'chpasswd' in cfg and 'list' in cfg['chpasswd']:
            del cfg['chpasswd']['list']
    else:
        password = util.get_cfg_option_str(cfg,"password",None)

    expire = True
    pw_auth = "no"
    change_pwauth = False
    plist = None

    if 'chpasswd' in cfg:
        chfg = cfg['chpasswd']
        plist = util.get_cfg_option_str(chfg,'list',plist)
        expire = util.get_cfg_option_bool(chfg,'expire', expire)

    if not plist and password:
        user = util.get_cfg_option_str(cfg,"user","ubuntu")
        plist = "%s:%s" % (user, password)

    errors = []
    if plist:
        plist_in = []
        randlist = []
        users = []
        for line in plist.splitlines():
            u,p = line.split(':',1)
            if p == "R" or p == "RANDOM":
                p = rand_user_password()
                randlist.append("%s:%s" % (u,p))
            plist_in.append("%s:%s" % (u,p))
            users.append(u)
        
        ch_in = '\n'.join(plist_in)
        try:
            util.subp(['chpasswd'], ch_in)
            log.debug("changed password for %s:" % users)
        except Exception as e:
            errors.append(e)
            log.warn("failed to set passwords with chpasswd: %s" % e)

        if len(randlist):
            sys.stdout.write("%s\n%s\n" % ("Set the following passwords\n",
                '\n'.join(randlist) ))

        if expire:
            enum=len(errors)
            for u in users:
                try:
                    util.subp(['passwd', '--expire', u])
                except Exception as e:
                    errors.append(e)
                    log.warn("failed to expire account for %s" % u )
            if enum == len(errors):
                log.debug("expired passwords for: %s" % u)

    if 'ssh_pwauth' in cfg:
        val = str(cfg['ssh_pwauth']).lower()
        if val in ( "true", "1", "yes"):
            pw_auth="yes"
            change_pwauth=True
        elif val in ( "false", "0", "no"):
            pw_auth="no"
            change_pwauth=True
        else:
            change_pwauth=False
            
    if change_pwauth:
        pa_s = "\(#*\)\(PasswordAuthentication[[:space:]]\+\)\(yes\|no\)"
        msg = "set PasswordAuthentication to '%s'" % pw_auth
        try:
            cmd = [ 'sed', '-i', 's,%s,\\2%s,' % (pa_s, pw_auth),
                    '/etc/ssh/sshd_config' ]
            util.subp(cmd)
            log.debug(msg)
        except Exception as e:
            log.warn("failed %s" % msg)
            errors.append(e)

        try:
            p = util.subp(['service', 'ssh', 'restart'])
            log.debug("restarted sshd")
        except:
            log.warn("restart of ssh failed")

    if len(errors):
        raise(errors[0])

    return

def rand_str(strlen=32, select_from=string.letters+string.digits):
    return("".join([random.choice(select_from) for x in range(0, strlen)]))

def rand_user_password(pwlen=9):
    selfrom=(string.letters.translate(None,'loLOI') +
             string.digits.translate(None,'01'))
    return(rand_str(pwlen,select_from=selfrom))
