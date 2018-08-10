package sandcrawler

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

//case class MapFeatures(slug : String, json : String)

class ScoreJob(args: Args) extends JobBase(args) { //with HBasePipeConversions {

  val grobidSource = HBaseCrossrefScore.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"))

  val source0 : Source = TextLine("foo")
  val pipe0 : cascading.pipe.Pipe = source0.read
  // This compiles:
  val pipe00 : TypedPipe[String] = getFeaturesPipe0(pipe0)

  // Calling a method within ScoreJob compiles fine.
  def getFeaturesPipe0(pipe : cascading.pipe.Pipe) : TypedPipe[String] = {
    pipe
    // This compiles:
      .toTypedPipe[String](new Fields("line"))
  }

  // Calling a function in a ScoreJob object leads to a compiler error.
  val source1 : Source = TextLine("foo")
  val pipe1 : cascading.pipe.Pipe = source1.read
  // This leads to a compile error:
  val pipe11 : TypedPipe[String] = ScoreJob.getFeaturesPipe1(pipe0)

  /*
  val pipe : cascading.pipe.Pipe = grobidSource
    .read
  val grobidPipe : TypedPipe[(String, String)] = pipe
    .fromBytesWritable(new Fields("key", "tei_json"))
  // Here I CAN call Pipe.toTypedPipe()
    .toTypedPipe[(String, String)]('key, 'tei_json)
    .write(TypedTsv[(String, String)](args("output")))

  // Let's try making a method call.
//  ScoreJob.etFeaturesPipe(pipe)

  // TODO: Instantiate any subclass of Scorable specified in args.
  Scorable sc1 = new GrobidScorable()
  Scorable sc2 = new CrossrefScorable()
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(sc1.getSource().read)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = sc2.getInputPipe(sc2.getSource().read)


  pipe1.join(pipe2).map { entry =>
    val (slug : String, (features1 : ReduceFeatures, features2 : ReduceFeatures)) = entry
    new ReduceOutput(
      slug,
      Scorable.computeSimilarity(features1, features2),
      features1.json,
      features2.json)
  }
    .write(TypedTsv[ReduceOutput](args("output")))
   */

}

// Ugly hack to get non-String information into ScoreJob above.
object ScoreJob {
  var scorable1 : Option[Scorable] = None
  var scorable2 : Option[Scorable] = None

  def setScorable1(s : Scorable) {
    scorable1 = Some(s)
  }

  def getScorable1() : Scorable = {
    scorable1  match {
      case Some(s) => s
      case None => null
    }
  }

  def setScorable2(s: Scorable) {
    scorable2 = Some(s)
  }

  def getScorable2() : Scorable = {
    scorable2 match {
      case Some(s) => s
      case None => null
    }
  }

  def getFeaturesPipe1(pipe : cascading.pipe.Pipe) : TypedPipe[String] = {
    pipe
    // The next line gives an error: value toTypedPipe is not a member of cascading.pipe.Pipe
      .toTypedPipe[String](new Fields("line"))
  }
/*
  def getFeaturesPipe(pipe : cascading.pipe.Pipe) : TypedPipe[MapFeatures] = {
    pipe
      .fromBytesWritable(new Fields("key", "tei_json"))
    // I needed to change symbols to strings when I pulled this out of ScoreJob.
      .toTypedPipe[(String, String)](new Fields("key", "tei_json"))
      .map { entry =>
        val (key : String, json : String) = (entry._1, entry._2)
        GrobidScorable.grobidToSlug(json) match {
          case Some(slug) => new MapFeatures(slug, json)
          case None => new MapFeatures(Scorable.NoSlug, json)
        }
      }
  }
 */
}
