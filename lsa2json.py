#!/usr/bin/env python

import re
import sys
import json

# LSA types prefix of a line
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
    
    def __init__(self) :
        self.rdb = {} # for router lsa
        self.ndb = {} # for network lsa
        # key is LSA ID, value is class LSA instance
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

def convert_lsadump_to_lsdb(dumpfile, lsdb) :

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
        lsa = lsdb.find_lsa(lsa_type, lsa_id)
        if not lsa :
            lsa = LSA(lsa_type = lsa_type, adv_router = d["ADVROUTER"],
                      lsa_id = lsa_id)
            lsdb.add_lsa(lsa)

        if lsa_type == ROUTER_LSA :
            rlink = RouterLSALink(link_type = d["LINKTYPE"],
                                  link_id = d["LINKID"],
                                  link_data = d["DATA"])
            lsa.add_router_link(rlink)

        if lsa_type == NETWORK_LSA :
            lsa.add_attached_router(d["ATTACHED"])

    f.close()
        
    return


def convert_lsdb_to_neighbor_info(lsdb) :

    """
    create a dict contains neighbor info for drawing adjacency matrix.
    { 
        ROUTERID: [ { "type": p2p|vlink|network, neighbor: ROUTERID},
                    { "type": p2p|vlink|network, neighbor: ROUTERID},
                     ...
                   ],
        ROUTERID...
    }

    trace router lsa link type 1 (point-to-pint, virtual link) and
    network lsa
    """
    
    neidb = {}

    # trace router lsa, link type 1 and 4
    for lsa_id, lsa in lsdb.rdb.items() :

        neidb[lsa.adv_router] = []

        for rlink in lsa.attached_links :
            if rlink.link_type == P2P_LINK :
                neidb[lsa.adv_router].append({"neighbor": rlink.link_id,
                                              "type": "p2p"})

            if rlink.link_type == VIRTUAL_LINK :
                neidb[lsa.adv_router].append({"neighbor": rlink.link_id,
                                              "type": "vlink"})

    # trace network lsa. in network lsa, attached routers must establish
    # neighbor each other (full mesh).
    for lsa_id, lsa in lsdb.ndb.items() :

        for src in lsa.attached_routers :
            for dst in lsa.attached_routers :
                if src == dst : continue
                if not dst in neidb[src] :
                    neidb[src].append({"neighbor": dst, "type": "network"})

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

    router_list = lsdb.rdb.keys()
    network_list = lsdb.ndb.keys()
    links = []

    # trace router lsa, link type 1 and 4
    for lsa_id, lsa in lsdb.rdb.items() :
        for rlink in lsa.attached_links :
            if rlink.link_type == P2P_LINK or rlink.link_type == VIRTUAL_LINK :
                links.append({"source": lsa_id, "destination": rlink.link_id})

    # trace network lsa.
    for lsa_id, lsa in lsdb.ndb.items() :
        for attached in lsa.attached_routers :
            links.append({"source": lsa_id, "destination": attached})

    return {"router_list": router_list, "network_list": network_list,
            "links": links }



if __name__ == '__main__' :

    if len(sys.argv) < 2:
        print "usage: lsa2json.py [lsadump output file]"
        sys.exit(1)

    lsdb = LSDB()
    convert_lsadump_to_lsdb(sys.argv[1], lsdb)

    #lsdb.dump()

    d = {
        "neighbor_info" : convert_lsdb_to_neighbor_info(lsdb),
        "graph_info": convert_lsdb_to_graph_info(lsdb),
    }

    print json.dumps(d, indent = 4)
