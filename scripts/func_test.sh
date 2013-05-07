#!/bin/bash

# A script for dumping basic information regarding environment sanity. 
# (c) OpenNode


# Verify if funcd is working
service funcd status
if [ $? -ne 0 ]; then 
    echo "==> Warning: FUNC daemon is not running, execution of remote calls is not possible."
fi

# Verify if certmasterd is working
service certmaster status
if [ $? -ne 0 ]; then
    echo "==> Warning: Certmaster daemon is not running. New requests will not be accepted."
fi

echo -e "\n[FUNC] CERTMASTER certificates and cert.requests"
ls --format=single-column /etc/pki/certmaster/ | egrep ".cert|.csr"

echo -e "\n[FUNC] Configured certmaster server:"
grep ^certmaster /etc/certmaster/minion.conf 

echo -e "\n[FUNC] Checking for possible registration conflict"
samemachine=`ls /etc/pki/certmaster/$HOSTNAME.cert 2> /dev/null`
if [ $? -eq 0 ]; then
    echo -e "==> Warning: It seems that FUNC and Certmaster hosts are the same."
    echo -e "New requests from this host will be ignored. Try 'rm $samemachine' for removing existing certificate."
    echo -e "After deletion restart funcd: 'service funcd restart'"
fi

echo -e "\n[CERTMASTER] List of existing certificate requests:"
ls --format=single-column /var/lib/certmaster/certmaster/csrs/

# Check signed certreqs
echo -e "\n[CERTMASTER] List of signed certificates:"
ls --format=single-column /var/lib/certmaster/certmaster/certs/
