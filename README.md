# synth
An IoT device simulator. Generates realistic historical usage data, and can emulate devices live. Useful for load-testing, regression-testing and demonstration of IoT services. 

To test that Synth is installed correctly:

1) Create an account file at ../synth_accounts/OnFStest containing:
{
	"instance_name" : "OnFStest",
	"client" :
	{
		"type" : "filesystem",
		"filename" :"OnFStest"
	}
}

2) Ensure there's a scenario file in scenarios/10secs containing:
{
    "device_count" : 10,
    "start_time" : "now",
    "end_time" : "PT10S",
    "install_timespan" : 10
}

3) Now on the command line run:
   python synth OnFStest 10secs

This will run for 10 seconds and create the file ../synth_logs/OnFStest.csv
