# yousee-epg-downloader

This program will download a file everytime it is run, and only store it if it differs from the last
one downloaded. A range of checks are performed:
* age of last file
* file size validation
* xml validation with xmllint

This is meant to be run by cron at an interval matching the "EpgAgeLimit"-setting.

## basic usage

    ./yousee-epg-downloader path-to-epg-config.json


## configuration

Configuration is made with a json-file, that could look a bit like this:

The value EpgAgeLimit and -WiggleRoom is interpreted as a number of hours, EpgMinSize and EpgMaxSize as size in bytes.
Double-quotes have intentionally been left out from the before-mentioned settings.

```json
{
    "Username": "..",
    "Password": "..",
    "EpgUrl" : "http://194.239.141.37/statsbiblioteket/epg.xml",
    "DataDir": "/path/to/yousee/epg/data/dir",
    "TrashDir": "/path/to/broken/yousee/epg/data/dir",
    "LogFile": "/var/log/yousee-epg-downlodaer.log",
    "StateMonitor": "http://canopus:9511/workflowstatemonitor",
    "EpgAgeLimit": 24,
    "EpgAgeLimitWiggleRoom": 1,
    "EpgMinSize": 1000000,
    "EpgMaxSize": 10000000
}
```


### documentation of configuration options

* *Username:* Username for the yousee server
* *Password:* Password for the yousee server
* *EpgUrl:* File to fetch when run
* *DataDir:* Directory to store downloaded files in. Files will be split into directories named after the current year.
* *TrashDir:* Broken files will be moved here.
* *LogFile:* File used for logging.
* *StateMonitor:* URL for the yousee workflow state monitor, which is used for reported sucessful and failed downloads.
* *EpgAgeLimit:* Ideal max time between EPG downloads.
* *EpgAgeLimitWiggleRoom:* Files older than EpgAgeLimit+EpgAgeLimitWiggleRoom will cause the program to report missing epg files to the state monitor.
* *EpgMinSize:* Minimum size, in bytes, for the downloaded file.
* *EpgMaxSize:* Maximum size, in bytes, for the downloaded file.
