package sandcrawler

import cascading.flow.FlowDef
import cascading.pipe.Pipe
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidScorable extends Scorable with HBasePipeConversions {
  def getFeaturesPipe(args : Args)(implicit flowDef : FlowDef, mode : Mode) = {
    // TODO: Clean up code after debugging.
    val grobidSource = HBaseCrossrefScore.getHBaseSource(
      args("hbase-table"),
      args("zookeeper-hosts"))

//    val pipe0 : Pipe = grobidSource.read
//    val grobidPipe : TypedPipe[MapFeatures] = pipe0
    grobidSource.read
    .fromBytesWritable(new Fields("key", "tei_json"))
    //  .debug  // Should be 4 tuples for mocked data
    // TODO: Figure out why this line (used in HBaseCrossrefScoreJob.scala)
    // didn't work here: .toTypedPipe[(String, String)]('key, 'tei_json)
    .toTypedPipe[(String, String)](new Fields("key", "tei_json"))
    .map { entry =>
      val (key : String, json : String) = (entry._1, entry._2)
      HBaseCrossrefScore.grobidToSlug(json) match {
        case Some(slug) => new MapFeatures(slug, json)
        case None => new MapFeatures(Scorable.NoSlug, json)
      }
    }
  }
/*
  def fromBytesWritableLocal(f: Fields): Pipe = {
	asList(f)
	  .foldLeft(pipe) { (p, fld) => {
	    p.map(fld.toString -> fld.toString) { from: org.apache.hadoop.hbase.io.ImmutableBytesWritable =>
            Option(from).map(x => Bytes.toString(x.get)).getOrElse(null)
          }
      }}
  }
 */
}
