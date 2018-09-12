package sandcrawler

import cascading.tuple.Fields
import cascading.pipe.Pipe
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class ScoreInsertableJob(args: Args) extends JobBase(args) {

  val grobidRowCount = Stat("grobid-rows-filtered", "sandcrawler")
  val crossrefRowCount = Stat("crossref-rows-filtered", "sandcrawler")
  val cdxRowCount = Stat("cdx-rows", "sandcrawler")
  val scoredRowCount = Stat("scored-rows", "sandcrawler")
  val joinedRowCount = Stat("joined-rows", "sandcrawler")

  val grobidScorable : Scorable = new GrobidScorable()
  val crossrefScorable : Scorable = new CrossrefScorable()

  val grobidPipe : TypedPipe[(String, ReduceFeatures)] = grobidScorable
    .getInputPipe(args)
    .map { r =>
      grobidRowCount.inc
      r
    }
  val crossrefPipe : TypedPipe[(String, ReduceFeatures)] = crossrefScorable
    .getInputPipe(args)
    .map { r =>
      crossrefRowCount.inc
      r
    }
  val cdxPipe : TypedPipe[(String, String, String, Long)] = ScoreInsertableJob.getHBaseCdxSource(args("hbase-table"), args("zookeeper-hosts"))
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "cdx", "mime", "size"))
    .filter { case (_, cdx, mime, size) => cdx != null && mime != null && size != null }
    .map { case (key, cdx, mime, size) =>
      (Bytes.toString(key.copyBytes()),
       Bytes.toString(cdx.copyBytes()),
       Bytes.toString(mime.copyBytes()),
       Bytes.toLong(size.copyBytes()))
    }
    .map { r =>
      cdxRowCount.inc
      r
    }

  val scoredPipe = grobidPipe
    .addTrap(TypedTsv(args("output") + ".trapped"))
    .join(crossrefPipe)
    .map { case (slug, (grobidFeatures, crossrefFeatures)) =>
      scoredRowCount.inc
      //val (slug : String, (grobidFeatures: ReduceFeatures, crossrefFeatures: ReduceFeatures)) = entry
      // Not ever Empty, I promise
      val key = Scorable.getStringOption(Scorable.jsonToMap(grobidFeatures.json), "sha1").orNull
      (key, new ReduceOutput(
        slug,
        Scorable.computeSimilarity(grobidFeatures, crossrefFeatures),
        grobidFeatures.json,
        crossrefFeatures.json))
    }
    .map { case (key, entry) => (key, entry.slug, entry.score, entry.json1, entry.json2) }
    .groupBy { case (key, _, _, _, _) => key }

  // TypedTsv doesn't work over case classes.
  val joinedPipe = scoredPipe
    .join(cdxPipe.groupBy { case (key, _, _, _) => key })
    .map { case (key, ((_, slug, score, left, right), (_, cdx, mime, size))) => (key, slug, score, left, right, cdx, mime, size) }
    .write(TypedTsv[(String, String, Int, String, String, String, String, Long)](args("output")))
}

object ScoreInsertableJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseCdxSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("file:cdx", "file:mime", "file:size"),
      SourceMode.SCAN_ALL)
  }
}
