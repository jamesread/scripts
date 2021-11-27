#!/bin/bash

./teratan-supermicro.yml -e SERVER_BMC=hydra-tr-bmc -e SERVER_IP=hydra-tr
./teratan-supermicro.yml -e SERVER_BMC=hydra-tl-bmc -e SERVER_IP=hydra-tl
./teratan-supermicro.yml -e SERVER_BMC=hydra-bl-bmc -e SERVER_IP=hydra-bl
./teratan-supermicro.yml -e SERVER_BMC=hydra-br-bmc -e SERVER_IP=hydra-br
