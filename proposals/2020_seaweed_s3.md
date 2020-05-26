# Notes on seaweedfs

> 2020-04-28, martin@archive.org

Currently (04/2020) [minio](https://github.com/minio/minio) is used to store
output from PDF analysis for [fatcat](https://fatcat.wiki) (e.g. from
[grobid](https://grobid.readthedocs.io/en/latest/)). The file checksum (sha1)
serves as key, values are blobs of XML or JSON.

Problem: minio inserts slowed down after inserting 80M or more objects.

Summary: I did four test runs, three failed, one (testrun-4) succeeded.

* [testrun-4](https://git.archive.org/webgroup/sandcrawler/-/blob/martin-seaweed-s3/proposals/2020_seaweed_s3.md#testrun-4)

So far, in a non-distributed mode, the project looks usable. Added 200M objects
(about 550G) in 6 days. Full CPU load, 400M RAM usage, constant insert times.

----

Details (03/2020) / @bnewbold, slack

> the sandcrawler XML data store (currently on aitio) is grinding to a halt, I
> think because despite tuning minio+ext4+hdd just doesn't work. current at 2.6
> TiB of data (each document compressed with snappy) and 87,403,183 objects.

> this doesn't impact ingest processing (because content is queued and archived
> in kafka), but does impact processing and analysis

> it is possible that the other load on aitio is making this worse, but I did
> an experiment with dumping to a 16 TB disk that slowed way down after about
> 50 million files also. some people on the internet said to just not worry
> about these huge file counts on modern filesystems, but i've debugged a bit
> and I think it is a bad idea after all

Possible solutions

* putting content in fake WARCs and trying to do something like CDX
* deploy CEPH object store (or swift, or any other off-the-shelf object store)
* try putting the files in postgres tables, mongodb, cassandra, etc: these are
  not designed for hundreds of millions of ~50 KByte XML documents (5 - 500
  KByte range)
* try to find or adapt an open source tool like Haystack, Facebook's solution
  to this engineering problem. eg:
  https://engineering.linkedin.com/blog/2016/05/introducing-and-open-sourcing-ambry---linkedins-new-distributed-

----

The following are notes gathered during a few test runs of seaweedfs in 04/2020
on wbgrp-svc170.us.archive.org (4 core E5-2620 v4, 4GB RAM).

----

## Setup

There are frequent [releases](https://github.com/chrislusf/seaweedfs/releases)
but for the test, we used a build off the master branch.

Directions from configuring AWS CLI for seaweedfs:
[https://github.com/chrislusf/seaweedfs/wiki/AWS-CLI-with-SeaweedFS](https://github.com/chrislusf/seaweedfs/wiki/AWS-CLI-with-SeaweedFS).

### Build the binary

Using development version (requires a [Go installation](https://golang.org/dl/)).

```
$ git clone git@github.com:chrislusf/seaweedfs.git # 11f5a6d9
$ cd seaweedfs
$ make
$ ls -lah weed/weed
-rwxr-xr-x 1 tir tir 55M Apr 17 16:57 weed

$ git rev-parse HEAD
11f5a6d91346e5f3cbf3b46e0a660e231c5c2998

$ sha1sum weed/weed
a7f8f0b49e6183da06fc2d1411c7a0714a2cc96b
```

A single, 55M binary emerges after a few seconds. The binary contains
subcommands to run different parts of seaweed, e.g. master or volume servers,
filer and commands for maintenance tasks, like backup and compact.

To *deploy*, just copy this binary to the destination.

### Quickstart with S3

Assuming `weed` binary is in PATH.

Start a master and volume server (over /tmp, most likely) and the S3 API with a single command:

```
$ weed -server s3
...
Start Seaweed Master 30GB 1.74 at 0.0.0.0:9333
...
Store started on dir: /tmp with 0 volumes max 7
Store started on dir: /tmp with 0 ec shards
Volume server start with seed master nodes: [localhost:9333]
...
Start Seaweed S3 API Server 30GB 1.74 at http port 8333
...
```

Install the [AWS
CLI](https://github.com/chrislusf/seaweedfs/wiki/AWS-CLI-with-SeaweedFS).
Create a bucket.

```
$ aws --endpoint-url http://localhost:8333 s3 mb s3://sandcrawler-dev
make_bucket: sandcrawler-dev
```

List buckets.

```
$ aws --endpoint-url http://localhost:8333 s3 ls
2020-04-17 17:44:39 sandcrawler-dev
```

Create a dummy file.

```
$ echo "blob" > 12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml
```

Upload.

```
$ aws --endpoint-url http://localhost:8333 s3 cp 12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml s3://sandcrawler-dev
upload: ./12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml to s3://sandcrawler-dev/12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml
```

List.

```
$ aws --endpoint-url http://localhost:8333 s3 ls s3://sandcrawler-dev
2020-04-17 17:50:35          5 12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml
```

Stream to stdout.

```
$ aws --endpoint-url http://localhost:8333 s3 cp s3://sandcrawler-dev/12340d9a4a4f710ecf03b127051814385e83ff08.tei.xml -
blob
```

Drop the bucket.

```
$ aws --endpoint-url http://localhost:8333 s3 rm --recursive s3://sandcrawler-dev
```

### Builtin benchmark

The project comes with a builtin benchmark command.

```
$ weed benchmark
```

I encountered an error like
[#181](https://github.com/chrislusf/seaweedfs/issues/181), "no free volume
left" - when trying to start the benchmark after the S3 ops. A restart or a restart with `-volume.max 100` helped.

```
$ weed server -s3 -volume.max 100
```

### Listing volumes

```
$ weed shell
> volume.list
Topology volume:15/112757 active:8 free:112742 remote:0 volumeSizeLimit:100 MB
  DataCenter DefaultDataCenter volume:15/112757 active:8 free:112742 remote:0
    Rack DefaultRack volume:15/112757 active:8 free:112742 remote:0
      DataNode localhost:8080 volume:15/112757 active:8 free:112742 remote:0
        volume id:1 size:105328040 collection:"test" file_count:33933 version:3 modified_at_second:1587215730
        volume id:2 size:106268552 collection:"test" file_count:34236 version:3 modified_at_second:1587215730
        volume id:3 size:106290280 collection:"test" file_count:34243 version:3 modified_at_second:1587215730
        volume id:4 size:105815368 collection:"test" file_count:34090 version:3 modified_at_second:1587215730
        volume id:5 size:105660168 collection:"test" file_count:34040 version:3 modified_at_second:1587215730
        volume id:6 size:106296488 collection:"test" file_count:34245 version:3 modified_at_second:1587215730
        volume id:7 size:105753288 collection:"test" file_count:34070 version:3 modified_at_second:1587215730
        volume id:8 size:7746408 file_count:12 version:3 modified_at_second:1587215764
        volume id:9 size:10438760 collection:"test" file_count:3363 version:3 modified_at_second:1587215788
        volume id:10 size:10240104 collection:"test" file_count:3299 version:3 modified_at_second:1587215788
        volume id:11 size:10258728 collection:"test" file_count:3305 version:3 modified_at_second:1587215788
        volume id:12 size:10240104 collection:"test" file_count:3299 version:3 modified_at_second:1587215788
        volume id:13 size:10112840 collection:"test" file_count:3258 version:3 modified_at_second:1587215788
        volume id:14 size:10190440 collection:"test" file_count:3283 version:3 modified_at_second:1587215788
        volume id:15 size:10112840 collection:"test" file_count:3258 version:3 modified_at_second:1587215788
      DataNode localhost:8080 total size:820752408 file_count:261934
    Rack DefaultRack total size:820752408 file_count:261934
  DataCenter DefaultDataCenter total size:820752408 file_count:261934
total size:820752408 file_count:261934
```

### Custom S3 benchmark

To simulate the use case of S3 use case for 100-500M small files (grobid xml,
pdftotext, ...), I created a synthetic benchmark.

* [https://gist.github.com/miku/6f3fee974ba82083325c2f24c912b47b](https://gist.github.com/miku/6f3fee974ba82083325c2f24c912b47b)

We just try to fill up the datastore with millions of 5k blobs.

----

### testrun-1

Small set, just to run. Status: done. Learned that the default in memory volume
index grows too quickly for the 4GB machine.

```
$ weed server -dir /tmp/martin-seaweedfs-testrun-1 -s3 -volume.max 512 -master.volumeSizeLimitMB 100
```

* https://github.com/chrislusf/seaweedfs/issues/498 -- RAM
* at 10M files, we already consume ~1G

```
-volume.index string
        Choose [memory|leveldb|leveldbMedium|leveldbLarge] mode for memory~performance balance. (default "memory")
```

### testrun-2

200M 5k objects, in-memory volume index. Status: done. Observed: After 18M
objects the 512 100MB volumes are exhausted and seaweedfs will not accept any
new data.

```
$ weed server -dir /tmp/martin-seaweedfs-testrun-2 -s3 -volume.max 512 -master.volumeSizeLimitMB 100
...
I0418 12:01:43  1622 volume_loading.go:104] loading index /tmp/martin-seaweedfs-testrun-2/test_511.idx to memory
I0418 12:01:43  1622 store.go:122] add volume 511
I0418 12:01:43  1622 volume_layout.go:243] Volume 511 becomes writable
I0418 12:01:43  1622 volume_growth.go:224] Created Volume 511 on topo:DefaultDataCenter:DefaultRack:localhost:8080
I0418 12:01:43  1622 master_grpc_server.go:158] master send to master@[::1]:45084: url:"localhost:8080" public_url:"localhost:8080" new_vids:511
I0418 12:01:43  1622 master_grpc_server.go:158] master send to filer@::1:18888: url:"localhost:8080" public_url:"localhost:8080" new_vids:511
I0418 12:01:43  1622 store.go:118] In dir /tmp/martin-seaweedfs-testrun-2 adds volume:512 collection:test replicaPlacement:000 ttl:
I0418 12:01:43  1622 volume_loading.go:104] loading index /tmp/martin-seaweedfs-testrun-2/test_512.idx to memory
I0418 12:01:43  1622 store.go:122] add volume 512
I0418 12:01:43  1622 volume_layout.go:243] Volume 512 becomes writable
I0418 12:01:43  1622 master_grpc_server.go:158] master send to master@[::1]:45084: url:"localhost:8080" public_url:"localhost:8080" new_vids:512
I0418 12:01:43  1622 master_grpc_server.go:158] master send to filer@::1:18888: url:"localhost:8080" public_url:"localhost:8080" new_vids:512
I0418 12:01:43  1622 volume_growth.go:224] Created Volume 512 on topo:DefaultDataCenter:DefaultRack:localhost:8080
I0418 12:01:43  1622 node.go:82] topo failed to pick 1 from  0 node candidates
I0418 12:01:43  1622 volume_growth.go:88] create 7 volume, created 2: No enough data node found!
I0418 12:04:30  1622 volume_layout.go:231] Volume 511 becomes unwritable
I0418 12:04:30  1622 volume_layout.go:231] Volume 512 becomes unwritable
E0418 12:04:30  1622 filer_server_handlers_write.go:69] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
I0418 12:04:30  1622 filer_server_handlers_write.go:120] fail to allocate volume for /buckets/test/k43731970, collection:test, datacenter:
E0418 12:04:30  1622 filer_server_handlers_write.go:69] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
E0418 12:04:30  1622 filer_server_handlers_write.go:69] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
E0418 12:04:30  1622 filer_server_handlers_write.go:69] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
E0418 12:04:30  1622 filer_server_handlers_write.go:69] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
I0418 12:04:30  1622 masterclient.go:88] filer failed to receive from localhost:9333: rpc error: code = Unavailable desc = transport is closing
I0418 12:04:30  1622 master_grpc_server.go:276] - client filer@::1:18888
```

Inserted about 18M docs, then:

```
worker-0        @3720000        45475.13        81.80
worker-1        @3730000        45525.00        81.93
worker-3        @3720000        45525.76        81.71
worker-4        @3720000        45527.22        81.71
Process Process-1:
Traceback (most recent call last):
  File "/usr/lib/python3.5/multiprocessing/process.py", line 249, in _bootstrap
    self.run()
  File "/usr/lib/python3.5/multiprocessing/process.py", line 93, in run
    self._target(*self._args, **self._kwargs)
  File "s3test.py", line 42, in insert_keys
    s3.Bucket(bucket).put_object(Key=key, Body=data)
  File "/home/martin/.virtualenvs/6f3fee974ba82083325c2f24c912b47b/lib/python3.5/site-packages/boto3/resources/factory.py", line 520, in do_action
    response = action(self, *args, **kwargs)
  File "/home/martin/.virtualenvs/6f3fee974ba82083325c2f24c912b47b/lib/python3.5/site-packages/boto3/resources/action.py", line 83, in __call__
    response = getattr(parent.meta.client, operation_name)(**params)
  File "/home/martin/.virtualenvs/6f3fee974ba82083325c2f24c912b47b/lib/python3.5/site-packages/botocore/client.py", line 316, in _api_call
    return self._make_api_call(operation_name, kwargs)
  File "/home/martin/.virtualenvs/6f3fee974ba82083325c2f24c912b47b/lib/python3.5/site-packages/botocore/client.py", line 626, in _make_api_call
    raise error_class(parsed_response, operation_name)
botocore.exceptions.ClientError: An error occurred (InternalError) when calling the PutObject operation (reached max retries: 4): We encountered an internal error, please try again.

real    759m30.034s
user    1962m47.487s
sys     105m21.113s
```

Sustained 400 S3 puts/s, RAM usage 41% of a 4G machine. 56G on disk.

> No free volumes left! Failed to allocate bucket for /buckets/test/k163721819

### testrun-3

* use leveldb, leveldbLarge
* try "auto" volumes
* Status: done. Observed: rapid memory usage.

```
$ weed server -dir /tmp/martin-seaweedfs-testrun-3 -s3 -volume.max 0 -volume.index=leveldbLarge -filer=false -master.volumeSizeLimitMB 100
```

Observations: memory usage grows rapidly, soon at 15%.

Note-to-self: [https://github.com/chrislusf/seaweedfs/wiki/Optimization](https://github.com/chrislusf/seaweedfs/wiki/Optimization)

### testrun-4

The default volume size is 30G (and cannot be more at the moment), and RAM
grows very much with the number of volumes. Therefore, keep default volume size
and do not limit number of volumes `-volume.max 0` and do not use in-memory
index (rather leveldb)

Status: done, 200M object upload via Python script sucessfully in about 6 days,
memory usage was at a moderate 400M (~10% of RAM). Relatively constant
performance at about 400 `PutObject` requests/s (over 5 threads, each thread
was around 80 requests/s; then testing with 4 threads, each thread got to
around 100 requests/s).

```
$ weed server -dir /tmp/martin-seaweedfs-testrun-4 -s3 -volume.max 0 -volume.index=leveldb
```

The test script command was (40M files per worker, 5 workers).

```
$ time python s3test.py -n 40000000 -w 5 2> s3test.4.log
...

real    8454m33.695s
user    21318m23.094s
sys     1128m32.293s
```

The test script adds keys from `k0...k199999999`.

```
$ aws --endpoint-url http://localhost:8333 s3 ls s3://test | head -20
2020-04-19 09:27:13       5000 k0
2020-04-19 09:27:13       5000 k1
2020-04-19 09:27:13       5000 k10
2020-04-19 09:27:15       5000 k100
2020-04-19 09:27:26       5000 k1000
2020-04-19 09:29:15       5000 k10000
2020-04-19 09:47:49       5000 k100000
2020-04-19 12:54:03       5000 k1000000
2020-04-20 20:14:10       5000 k10000000
2020-04-22 07:33:46       5000 k100000000
2020-04-22 07:33:46       5000 k100000001
2020-04-22 07:33:46       5000 k100000002
2020-04-22 07:33:46       5000 k100000003
2020-04-22 07:33:46       5000 k100000004
2020-04-22 07:33:46       5000 k100000005
2020-04-22 07:33:46       5000 k100000006
2020-04-22 07:33:46       5000 k100000007
2020-04-22 07:33:46       5000 k100000008
2020-04-22 07:33:46       5000 k100000009
2020-04-20 20:14:10       5000 k10000001
```

Glance at stats.

```
$ du -hs /tmp/martin-seaweedfs-testrun-4
596G    /tmp/martin-seaweedfs-testrun-4

$ find . /tmp/martin-seaweedfs-testrun-4 | wc -l
5104

$ ps --pid $(pidof weed) -o pid,tid,class,stat,vsz,rss,comm
  PID   TID CLS STAT    VSZ   RSS COMMAND
32194 32194 TS  Sl+  1966964 491644 weed

$ ls -1 /proc/$(pidof weed)/fd | wc -l
192

$ free -m
              total        used        free      shared  buff/cache   available
Mem:           3944         534         324          39        3086        3423
Swap:          4094          27        4067
```

### Note on restart

When stopping (CTRL-C) and restarting `weed` it will take about 10 seconds to
get the S3 API server back up, but another minute or two, until seaweedfs
inspects all existing volumes and indices.

In that gap, requests to S3 will look like internal server errors.

```
$ aws --endpoint-url http://localhost:8333 s3 cp s3://test/k100 -
download failed: s3://test/k100 to - An error occurred (500) when calling the
GetObject operation (reached max retries: 4): Internal Server Error
```

### Read benchmark

Reading via command line `aws` client is a bit slow at first sight (3-5s).

```
$ time aws --endpoint-url http://localhost:8333 s3 cp s3://test/k123456789 -
ppbhjgzkrrgwagmjsuwhqcwqzmefybeopqz [...]

real    0m5.839s
user    0m0.898s
sys     0m0.293s
```

#### Single process random reads

Running 1000 random reads takes 49s.

#### Concurrent random reads

* 80000 request with 8 parallel processes: 7m41.973968488s, so about 170 objects/s)
* seen up to 760 keys/s reads for 8 workers
* weed will utilize all cores, so more cpus could result in higher read throughput
* RAM usage can increase (seen up to 20% of 4G RAM), then descrease (GC) back to 5%, depending on query load
