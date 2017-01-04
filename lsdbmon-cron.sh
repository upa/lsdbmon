
# Dump lsdb info through lsadump -> lsa2json -> lsadump.json

LSADUMP=/usr/local/sbin/lsadump
LSA2JSON=/usr/local/sbin/lsa2json.py

DUMPFILE_NEW=/tmp/lsadump.new.txt
DUMPFILE_OLD=/tmp/lsadump.old.txt

LOGFILE=/var/log/lsdbmon.log
JSONFILE=/tmp/lsadump.json

# backup old lsadump file
if [ -e $DUMPFILE_OLD ]; then
	rm $DUMPFILE_OLD
fi

if [ -e $DUMPFILE_NEW ]; then
	mv $DUMPFILE_NEW $DUMPFILE_OLD
fi


# dump LSAs to dump file
$LSADUMP 127.0.0.1 > $DUMPFILE_NEW


# generate json file from dump files
if [ -e $DUMPFILE_OLD ]; then
	$LSA2JSON -d $DUMPFILE_NEW -o $DUMPFILE_OLD -l $LOGFILE > $JSONFILE
else
	$LSA2JSON -d $DUMPFILE_NEW > $JSONFILE
fi
