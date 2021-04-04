# Random Forest - IDS

This is an Intrution Detection System with Machine Learning Based (Random Forest). This IDS used to detect DDoS Attack in Software-Defined Network with utilizing sFlow-RT (sFlow protocol). The analyze of Machine Learning Model can be found here: https://github.com/nadhirfr/cic-ids-2018

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/H2H146AUD)

Feature:
- Django Framework
- API (WebSocket and HTTP)
- Realtime Attack Alert
- Read Traffic from sFlow-RT
- Full async process (Django-Channels)

Dashboard ![Dashboard](https://image.prntscr.com/image/fQguG-P3SJGxSH2Gvxnglw.png)
Log ![Log](https://image.prntscr.com/image/cS07jXgeTIC9FINCFCpaFQ.png)

__HTTP API Documentation:__

| URL :      | http://ip_address/api/?sec=latestLog&limit=limitShow |
|------------|------------------------------------------------------|
| Method :   | GET                                                  |
| Example :  | http://127.0.0.1/api/?sec=10&limit=5                 |
|            | Get 5 data in last 10 seconds                        |

*GET status of service : http://ip_address/api/status/*

__WS Access URL : ws://ip_address/ws/api/__
