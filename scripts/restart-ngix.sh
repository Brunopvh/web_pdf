#!/bin/bash

sudo systemctl restart nginx
sudo nginx -t; sudo systemctl reload nginx

# sudo systemctl status nginx.service; sudo journalctl -xeu nginx.service


