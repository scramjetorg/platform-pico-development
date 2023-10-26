## File copying 

To copy required files to Raspberry use `rsync`. In WSL run:

```
rsync -av <PATH ON YOUR COPUTER>/platform-pico-development/milestones/VDM/ rg@<PICO IP>:/home/rg/VDM
```
