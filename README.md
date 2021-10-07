# tesla_nearby_superchargers

1. Create a logs folder
2. Rename config.json.sample to config.json
3. Use Tesla Tokens to generate the Owner API Access Token
4. Copy that value into config.json
5. Add the required libs inside requirements.txt
6. Simply run it

Go to https://developer.twitter.com/en/portal/dashboard to create a new project.
Under Keys and tokens, generate the following and record them somewhere:
1. consumer keys - api key
2. consumer keys - secret
3. access token
4. access token secret

Populate them into config.json

To run it inside a linux box, you can use the following steps:
1. mkdir ~/git
2. cd ~/git
3. git clone https://github.com/ashlord666/tesla_nearby_superchargers.git
4. cp config.json.sample config.json
5. update contents of config.json
6. python3 -m venv venv
7. . venv/bin/activate
8. pip3 install wheel
9. pip3 install -r requirements.txt
10. mkdir logs
11. try a manual run: cd /home/xxx/git/tesla_nearby_superchargers/ && venv/bin/python3 get_supercharger_status.py
12. check logs in /home/xxx/git/tesla_nearby_superchargers/logs/ to make sure everything is fine
13. add this entry to crontab: */3 * * * * cd /home/xxx/git/tesla_nearby_superchargers/ && venv/bin/python3 get_supercharger_status.py > /dev/null 2>&1

Note: The script is quite basic and doesn't handle token refresh in case you are using it with something else, e.g. Teslamate. You will need to manually refresh the Owner API Access Token.