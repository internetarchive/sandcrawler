package sandcrawler

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding.{Args,Source,TextLine,TypedPipe, TypedTsv}
//import com.twitter.scalding.source.TypedText
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource
import com.twitter.scalding.{ Dsl, RichPipe, IterableSource, TupleSetter, TupleConverter }
import cascading.pipe.Pipe

class ScoreJob(args: Args) extends JobBase(args) { //with HBasePipeConversions {
  // TODO: Instantiate any subclass of Scorable specified in args.
  val sc1 : Scorable = new GrobidScorable()
  val sc2 : Scorable = new CrossrefScorable()
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(args)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = sc2.getInputPipe(args)

  pipe1.join(pipe2).map { entry =>
    val (slug : String, (features1 : ReduceFeatures, features2 : ReduceFeatures)) = entry
    new ReduceOutput(
      slug,
      Scorable.computeSimilarity(features1, features2),
      features1.json,
      features2.json)
  }
  //TypedTsv doesn't work over case classes.
    .map { entry => (entry.slug, entry.score, entry.json1, entry.json2) }

    .write(TypedTsv[(String, Int, String, String)](args("output")))
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

  /*
  implicit def sourceToRichPipe(src: Source): RichPipe = new RichPipe(src.read)

  // This converts an Iterable into a Pipe or RichPipe with index (int-based) fields
  implicit def toPipe[T](iter: Iterable[T])(implicit set: TupleSetter[T], conv: TupleConverter[T]): Pipe =
    IterableSource[T](iter)(set, conv).read

  implicit def iterableToRichPipe[T](iter: Iterable[T])(implicit set: TupleSetter[T], conv: TupleConverter[T]): RichPipe =
    RichPipe(toPipe(iter)(set, conv))

  // Provide args as an implicit val for extensions such as the Checkpoint extension.
//  implicit protected def _implicitJobArgs: Args = args

  def getFeaturesPipe1(pipe : cascading.pipe.Pipe) : TypedPipe[String] = {
    pipe
    // The next line gives an error: value toTypedPipe is not a member of cascading.pipe.Pipe
      .toTypedPipe[String](new Fields("line"))
  }

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
