package sandcrawler

import com.twitter.scalding._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions, HBaseConstants}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import cascading.tuple.Fields
import cascading.property.AppProps
import java.util.Properties


class HBaseRowCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {


  // For now doesn't actually count, just dumps a "word count"

  val output = args("output")

  val hbs = new HBaseSource(
    //"table_name",
    //"quorum_name:2181",
    "wbgrp-journal-extract-0-qa",     // HBase Table Name
    "mtrcs-zk1.us.archive.org:2181",  // HBase Zookeeper server (to get runtime config info; can be array?)
    new Fields("key"),
    List("file"),
    List(new Fields("size", "mimetype")),
    sourceMode = SourceMode.GET_LIST, keyList = List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", "sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU"))
    .read
    .debug
    .fromBytesWritable(new Fields("key"))
    .write(Tsv(output format "get_list"))

    /*
    List("column_family"),
    sourceMode = SourceMode.SCAN_ALL)
    .read
    .debug
    .fromBytesWritable(new Fields("key"))
    .write(Tsv(output format "get_list"))
    */
}
