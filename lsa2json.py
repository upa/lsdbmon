#!/usr/bin/env python

import re
import sys
import json
import socket
from optparse import OptionParser
from datetime import datetime

# LSA types
ROUTER_LSA = 1
NETWORK_LSA = 2

# Router LSA Link types
P2P_LINK = 1
TRANSIT_LINK = 2
STUB_LINK = 3
VIRTUAL_LINK = 4


class RouterLSALink :

    def __init__(self, link_type = None, link_id = None, link_data = None) :
        self.link_type = link_type
        self.link_id = link_id
        self.link_data = link_data
        return

class LSA :

    def __init__(self, lsa_type, adv_router = None, lsa_id = None) :

        self.lsa_type = lsa_type
        self.adv_router = adv_router
        self.lsa_id = lsa_id

        self.attached_links = [] # RouterLSALink list
        self.attached_routers = [] # Router ID List
        return

    def add_router_link(self, rlink) :
        self.attached_links.append(rlink)
        return
        
    def add_attached_router(self, attached) :
        self.attached_routers.append(attached)
        return
    

class LSDB :
    
    def __init__(self, *args) :
        self.rdb = {} # for router lsa
        self.ndb = {} # for network lsa
        # key is LSA ID, value is class LSA instance

        if args :
            self.load(args[0])

        return


    def which_db(self, lsa_type) :
        if lsa_type == ROUTER_LSA :
            return self.rdb
        elif lsa_type == NETWORK_LSA :
            return self.ndb

        print >> sys.stderr, ("not supported LSA type %d of lsa id %s" % 
                              (lsa.lsa_type, lsa.lsa_id))
        return None


    def add_lsa(self, lsa) :
        
        db = self.which_db(lsa.lsa_type)
        lsa_id = lsa.lsa_id

        if lsa_id in db :
            print >> sys.stderr, "duplicated LSA id %s" % lsa_id
            return False
        db[lsa_id] = lsa

        return


    def del_lsa(self, lsa_id) :

        db = self.which_db(lsa.lsa_type)

        if lsa_id in db :
            del(db[lsa_id])
        return


    def find_lsa(self, lsa_type, lsa_id) :
    
        if lsa_type == ROUTER_LSA :
            if lsa_id in self.rdb :
                return self.rdb[lsa_id]

        if lsa_type == NETWORK_LSA :
            if lsa_id in self.ndb :
                return self.ndb[lsa_id]

        return None
    
    def dump(self) :

        print "Dump Router LSA"
        for lsa_id, lsa in self.rdb.items() :
            print ("Router LSA: adv_router=%s, lsa_id=%s" %
                   (lsa.adv_router, lsa_id))
            for rlink in lsa.attached_links :
                print ("\tlink_type=%d, link_id=%s, link_data=%s"
                       % (rlink.link_type, rlink.link_id, rlink.link_data))
            print

        print "Dump Network LSA"
        for lsa_id, lsa in self.ndb.items() :
            print ("Network LSA: adv_router=%s, lsa_id=%s" %
                   (lsa.adv_router, lsa_id))
            print "\t%s" % ' '.join(lsa.attached_routers)
            print


    def load(self, dumpfile) :

        def line_to_dict(line) :
            d = {}
            s = line.strip().split(' ')
            for p in s :
                k, v = p.split('=')
                if re.match(r'^\d+$', v) : d[k] = int (v)
                else : d[k] = v
            return d

        f = open(dumpfile, 'r')

        for l in f :

            d = line_to_dict(l)
            lsa_type = d["LSATYPE"]
            lsa_id = d["LSAID"]
            lsa = self.find_lsa(lsa_type, lsa_id)
            if not lsa :
                lsa = LSA(lsa_type = lsa_type, adv_router = d["ADVROUTER"],
                          lsa_id = lsa_id)
                self.add_lsa(lsa)

            if lsa_type == ROUTER_LSA :
                rlink = RouterLSALink(link_type = d["LINKTYPE"],
                                      link_id = d["LINKID"],
                                      link_data = d["DATA"])
                lsa.add_router_link(rlink)

            if lsa_type == NETWORK_LSA :
                lsa.add_attached_router(d["ATTACHED"])

        f.close()
        return


def inet_itok(ip) :
    # convert ipv4 string to %03d.%03d.%03d.%03d for sorting
    l = map(int, ip.split('.'))
    return "%03d.%03d.%03d.%03d" % (l[0], l[1], l[2], l[3]) # hummmmm...

def convert_lsdb_to_neighbor_info(lsdb) :

    """
    create a dict contains neighbor info for drawing adjacency matrix.
    [ 
        { router_id: ROUTERID,
          neighbors: [
                        { "type": p2p|vlink|network, router_id: ROUTERID},
                        { "type": p2p|vlink|network, router_id: ROUTERID},
                        ...
                      ]
        },
        { router_id: ROUTERID, ...
    ]

    trace router lsa link type 1 (point-to-pint, virtual link) and
    network lsa
    """
    
    neidb = []
    nei_dict = {}

    # trace router lsa, link type 1 and 4
    for lsa_id, lsa in lsdb.rdb.items() :

        rtr = { "router_id": lsa_id, "neighbors": []}
        neidb.append(rtr)
        nei_dict[lsa_id] = rtr

        for rlink in lsa.attached_links :
            if rlink.link_type == P2P_LINK :
                rtr["neighbors"].append({"router_id": rlink.link_id,
                                         "type": "p2p"})

            if rlink.link_type == VIRTUAL_LINK :
                rtr["neighbors"].append({"router_id": rlink.link_id,
                                         "type": "vlink"})


    # trace network lsa. in network lsa, attached routers must establish
    # neighbor each other (full mesh).
    for lsa_id, lsa in lsdb.ndb.items() :

        for src in lsa.attached_routers :
            for dst in lsa.attached_routers :
                if src == dst : continue
                nei_dict[src]["neighbors"].append({"router_id": dst,
                                                   "type": "network"})

    # sort
    for rtr in neidb :
        rtr["neighbors"].sort(key = lambda nei: inet_itok(nei["router_id"]))
    neidb.sort(key = lambda rtr: inet_itok(rtr["router_id"]))

    return neidb



def convert_lsdb_to_neighbor_set(lsdb) :

    """
    create a dict contains neighbor info for drawing adjacency matrix.
    { 
        ROUTERID: (NEI_ID, NEI_ID, NEI_ID),
        ROUTERID...
    }

    trace router lsa link type 1 (point-to-pint, virtual link) and
    network lsa
    """
    
    neidb = {}

    # trace router lsa, link type 1 and 4
    for lsa_id, lsa in lsdb.rdb.items() :

        neidb[lsa_id] = set()

        for rlink in lsa.attached_links :
            if rlink.link_type == P2P_LINK or rlink.link_type == VIRTUAL_LINK :
                neidb[lsa_id].add(rlink.link_id)

    # trace network lsa. in network lsa, attached routers must establish
    # neighbor each other (full mesh).
    for lsa_id, lsa in lsdb.ndb.items() :

        for src in lsa.attached_routers :
            for dst in lsa.attached_routers :
                if src == dst : continue
                if not dst in neidb[src] :
                    neidb[src].add(dst)

    return neidb


def convert_lsdb_to_graph_info(lsdb) :

    """
    create a dict contains graph information for drawing topology map
    {
         "router_list": [ ROUTERID, ROUTERID, ... ],
         "network_list": [ DRINTFADDR, DRINTFADDR, ... ],
         "links": [
             "source": ROUTERID|DRINTFADDR, "destination": ROUTERID|DRINTFADDR,
             "source": ROUTERID|DRINTFADDR, "destination": ROUTERID|DRINTFADDR,
             ...
         ]
    }
    """

    links = []

    # trace router lsa, link type 1 and 4
    for lsa_id, lsa in lsdb.rdb.items() :
        for rlink in lsa.attached_links :
            if rlink.link_type == P2P_LINK or rlink.link_type == VIRTUAL_LINK :
                links.append({"source": "rtr:" + lsa_id,
                              "target": "rtr:" + rlink.link_id})

    # trace network lsa.
    for lsa_id, lsa in lsdb.ndb.items() :
        for attached in lsa.attached_routers :
            links.append({"source": "net:" + lsa_id,
                          "target": "rtr:" + attached})

    # generate node info
    nodes = []
    for x in lsdb.rdb.keys() : nodes.append({"id" : "rtr:" + x,
                                             "type" : "router",
                                             "name": x})
    for x in lsdb.ndb.keys() : nodes.append({"id" : "net:" + x,
                                             "type" : "network",
                                             "name": x})

    return {"nodes": nodes, "links": links }


def generate_in_addr_arpa(lsdb, use_arpa) :

    # generate node info

    arpa = {}

    def dig_x (ip) :
        if not use_arpa : return ip
        try : name = socket.gethostbyaddr(x)[0]
        except : name = ip
        return name

    for x in lsdb.rdb.keys() :
        arpa["rtr:" + x] = { "type" : "router",
                             "hostname":  dig_x(x)}

    for x in lsdb.ndb.keys() :
        arpa["net:" + x] = { "type" : "network",
                             "hostname": dig_x(x) }

    return arpa


def lsdb_diff(lsdb_new, lsdb_old) :

    """
    calculate diff of new lsdb and old lsdb

    """

    nnei = convert_lsdb_to_neighbor_set(lsdb_new)
    onei = convert_lsdb_to_neighbor_set(lsdb_old)

    lines = []
    new_adjacent = set()
    rem_adjacent = set()

    # find new adjacency
    for router_id, nei_set in nnei.items() :
        if not router_id in onei :
            lines.append("New Router %s with Neighbor %s" %
                         (router_id, ' '.join(nei_set)))
        else :
            new_nei = nei_set - onei[router_id]
            
            for nei in new_nei :
                new_adjacent.add(' '.join(sorted([router_id, nei])))

    for new_adj in new_adjacent :
        lines.append("New Adjacency %s" % new_adj)


    # find removed adjacency
    for router_id, nei_set in onei.items() :
        if not router_id in nnei :
            lines.append("Removed Router %s with Neighbor %s" %
                         (router_id, ' '.join(nei_set)))
        else :
            rem_nei = nei_set - nnei[router_id]
            for nei in rem_nei :
                rem_adjacent.add(' '.join(sorted([router_id, nei])))

    for rem_adj in rem_adjacent :
        lines.append("Removed Adjacency %s" % rem_adj)

    return lines


if __name__ == '__main__' :

    timestamp = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

    desc = "usage: %prog [options]"
    parser = OptionParser(desc)

    parser.add_option('-d', '--dumpfile', type = "string", default = None,
                      dest = 'dumpfile', help = "lsadump file name")
    parser.add_option('-o', '--old-dumpfile', type = "string", default = None,
                      dest = 'dumpfile_old', help = "old lsadump file name")
    parser.add_option('-l', '--log', type = "string", default = None,
                      dest = 'logfile', help = "dump diff log file name")
    parser.add_option('-n', '--no-lookup', action="store_false", 
                      default = True, dest = "use_arpa",
                      help = "disable DNS reverse lookup")


    (options, args) = parser.parse_args()

    if not options.dumpfile :
        print "-d [lsadump output file] is required"
        sys.exit(1)



    # calculate neighbor and graph information
    lsdb = LSDB(options.dumpfile)
    d = {
        "timestamp": timestamp,
        "neighbor_info" : convert_lsdb_to_neighbor_info(lsdb),
        "graph_info": convert_lsdb_to_graph_info(lsdb),
        "arpa_info" : generate_in_addr_arpa(lsdb, options.use_arpa),
    }


    # calculate adjacency diff
    if options.dumpfile_old :

        lsdb_old = LSDB(options.dumpfile_old)
        diff = lsdb_diff(lsdb, lsdb_old)

        if options.logfile :
            with open(options.logfile, 'a') as f :
                for l in diff :
                    f.write(timestamp + " " + l + "\n")
        else :
            d["diff_log"] = diff


    print json.dumps(d, indent = 4)
