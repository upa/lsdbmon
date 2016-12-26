/*
 * Dump Link State Advertisements through Zebra OSPF API.
 * implemented with quagga version 1.1.0
 */

#include <poll.h>

#include <zebra.h>
#include "prefix.h"
#include "privs.h"
#include "table.h"

#include "ospfd/ospfd.h"
#include "ospfd/ospf_asbr.h"
#include "ospfd/ospf_lsa.h"
#include "ospfd/ospf_lsdb.h"
#include "ospfd/ospf_api.h"
#include "ospfd/ospf_dump.h"
#include "ospf_apiclient.h"


#include "thread.h"

struct thread_master *master;	/* needed to compile */

struct ospf_lsdb *lsdb;		/* LSDB to contain LSAes*/


#define ASYNCPORT	40000
#define POLLTIMEOUT	500	/* 0.5 sec */

/* privileges struct. */
struct zebra_privs_t ospfd_privs = {
	.user		= NULL,
	.group		= NULL,
	.cap_num_p	= 0,
	.cap_num_i	= 0,
};





static void
lsa_update_callback(struct in_addr ifaddr, struct in_addr area_id,
		    u_char is_self_originated, struct lsa_header *lsah)
{
	struct ospf_lsa *lsa;

	/* store this LSA to LSDB */

	lsa = ospf_lsa_new();
	lsa->data = ospf_lsa_data_new(lsah->length);
	memcpy(lsa->data, lsah, lsah->length);

	ospf_lsdb_add(lsdb, lsa);
	return;
}


static void
dump_router_lsa(struct router_lsa *rlsa)
{
	int len, links;
	char advr[16], lsaid[16], linkid[16], data[16];
	struct router_lsa_link *rl;

	inet_ntop(AF_INET, &rlsa->header.adv_router, advr, sizeof(advr));
	inet_ntop(AF_INET, &rlsa->header.id, lsaid, sizeof(lsaid));

	len = ntohs(rlsa->header.length) - sizeof(struct lsa_header) - 4;
	links = ntohs(rlsa->links);

	/* iterate Links of this router LSA */
	for (rl = (struct router_lsa_link *)rlsa->link;
	     len > 0 && links > 0;
	     len -= sizeof(struct router_lsa_link), links--, rl++) {

		inet_ntop(AF_INET, &rl->link_id, linkid, sizeof(linkid));
		inet_ntop(AF_INET, &rl->link_data, data, sizeof(data));

		printf("LSATYPE=%d "
		       "ADVROUTER=%s "
		       "LSAID=%s "
		       "LINKTYPE=%d "
		       "LINKID=%s "
		       "DATA=%s\n",
		       OSPF_ROUTER_LSA, advr, lsaid,
		       rl->m[0].type, linkid, data);
	}


}

static void
dump_network_lsa(struct network_lsa *nlsa)
{
	int len;
	char advr[16], lsaid[16], ar[16];
	struct in_addr *attached;

	inet_ntop(AF_INET, &nlsa->header.adv_router, advr, sizeof(advr));
	inet_ntop(AF_INET, &nlsa->header.id, lsaid, sizeof(lsaid));

	len = ntohs(nlsa->header.length) - sizeof(struct lsa_header) - 4;

	for (attached = nlsa->routers; len > 0;
	     len -= sizeof(struct in_addr), attached++) {
		
		inet_ntop(AF_INET, attached, ar, sizeof(ar));

		printf("LSATYPE=%d "
		       "ADVROUTER=%s "
		       "LSAID=%s "
		       "ATTACHED=%s\n",
		       OSPF_NETWORK_LSA, advr, lsaid, ar);
	}

	return;
}

static void
lsdb_dump_neighbors(struct ospf_lsdb *lsdb)
{
	struct ospf_lsa *lsa;
	struct router_lsa *rlsa;
	struct network_lsa *nlsa;
	struct route_node *rn;	/* for LSDB iteration */

	/* dump router lsa link neighbor info */
	LSDB_LOOP (lsdb->type[OSPF_ROUTER_LSA].db, rn, lsa) {
		rlsa = (struct router_lsa *) lsa->data;
		dump_router_lsa(rlsa);
	}

	/* dump Network link neighbors info */
	LSDB_LOOP(lsdb->type[OSPF_NETWORK_LSA].db, rn, lsa) {
		nlsa = (struct network_lsa *) lsa->data;
		dump_network_lsa(nlsa);
	}

	return;
}


int
main (int argc, char **argv)
{
	int ret;
	struct pollfd x[1];
	struct ospf_apiclient *oc;

	if (argc < 2) {
		fprintf(stdout, "usage: lsadump [APISERVADDR]\n");
		return 0;
	}

	lsdb = ospf_lsdb_new();

	zprivs_init(&ospfd_privs);
	oc = ospf_apiclient_connect(argv[1], ASYNCPORT);
	if (!oc) {
		fprintf(stderr, "failed to connect api server %s\n", argv[1]);
		return -1;
	}
	ospf_apiclient_register_callback(oc, NULL, NULL, NULL, NULL, NULL,
					 lsa_update_callback, NULL);

	ospf_apiclient_sync_lsdb(oc);

	x[0].fd = oc->fd_async;
	x[0].events = POLLIN;

	while (1) {

		ret = poll (x, 1, POLLTIMEOUT);
		if (ret == 0) {
			/* poll time out. no more lsa */
			break;
		}

		ret = ospf_apiclient_handle_async(oc);
		if (ret < 0) {
			fprintf(stderr, "failed to handle asunc message\n");
			return -1;
		}
	}

	ospf_apiclient_close(oc);

	lsdb_dump_neighbors(lsdb);

	return 0;
}
