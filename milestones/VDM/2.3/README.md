
## Firewall changes

Open Windows command line with admin permissions:

Allow incoming TCP traffic for 8000 and 8001 port:

```
netsh advfirewall firewall add rule name="Allowing connections for 8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Allowing connections for 8001" dir=in action=allow protocol=TCP localport=8001
```


Create proxy/forward from external network interface to localhost

```
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=localhost connectport=8000
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8001 connectaddress=localhost connectport=8001
```


## File copying 

To copy required files to Raspberry use `rsync`. In WSL run:

```
rsync -av <PATH ON YOUR COPUTER>/platform-pico-development/milestones/VDM/ rg@<PICO IP>:/home/rg/VDM
```
