# acistash
ACI to Logstash

## Install ELK Dockers

	$ docker pull elasticsearch:latest
	$ docker pull kibana:latest
	$ docker pull logstash:latest
	
	$ docker run --name elasticsearch \
	  --restart always -p 9200:9200 -p 9300:9300 -d \
	  elasticsearch:latest
	$ docker run --name kibana \
	  --restart always -p 80:5601 --link elasticsearch:elasticsearch -d \
	  kibana:latest
	$ docker run -it --rm \
	  -p 8929:8929 --link elasticsearch:elasticsearch \
	  logstash -e 'input { tcp { port => 8929 codec => json } } output { stdout { codec => rubydebug } elasticsearch { hosts => ["elasticsearch:9200"] } }'

## Logstash Basic Configurations

	input {
		tcp {
			port => 8929
			codec => json 
		}
	}
	output {
		stdout {
			codec => rubydebug
		}
		elasticsearch {
			hosts => ["elasticsearch:9200"]
		}
	}

## Start Agent

### Usages

	usage: agent.py [-h] [-d] -l LOGSTASH [-e] [-r REFRESH] -a APIC -u USERNAME -p
	                PASSWORD -o OBJECTS [OBJECTS ...]
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -d, --debug           debug mode
	  -l LOGSTASH, --logstash LOGSTASH
	                        logstash ip address
	  -e, --eventmode       event trigger mode
	  -r REFRESH, --refresh REFRESH
	                        refresh seconds of dump mode
	  -a APIC, --apic APIC  apic ip address
	  -u USERNAME, --username USERNAME
	                        apic user
	  -p PASSWORD, --password PASSWORD
	                        apic password
	  -o OBJECTS [OBJECTS ...], --objects OBJECTS [OBJECTS ...]
	                        inspect target objects

### Execution

	$ python agent.py [OPTIONS] -l <LOGSTASH IP> -a <APIC IP> -u <USERNAME> -p <PASSWORD> -o OBJECT ...
