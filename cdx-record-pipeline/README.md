CDX Record Pipeline (GrobId Edition)
=====================================

Hadoop based pipeline to process PDFs from a specified IA CDX dataset

## Local mode example ##

```
cat -n /home/bnewbold/100k_random_gwb_pdf.cdx | ./cdx-record-pipeline.py
 
```

## Cluster mode example ##

```
input=100k_random_gwb_pdf.cdx
output=100k_random_gwb_pdf.out
lines_per_map=1000

hadoop jar /home/webcrawl/hadoop-2/hadoop-mapreduce/hadoop-streaming.jar
	-archives "hdfs://ia802400.us.archive.org:6000/lib/cdx-record-pipeline-venv.zip#cdx-record-pipeline-venv"
	-D mapred.reduce.tasks=0
	-D mapred.job.name=Cdx-Record-Pipeline
	-D mapreduce.job.queuename=extraction
	-D mapred.line.input.format.linespermap=${lines_per_map} 
	-inputformat org.apache.hadoop.mapred.lib.NLineInputFormat 
	-input ${input}
	-output ${output}
	-mapper cdx-record-pipeline.py
	-file cdx-record-pipeline.py

```

