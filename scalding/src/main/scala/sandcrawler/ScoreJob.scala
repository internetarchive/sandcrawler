package sandcrawler

import cascading.flow.FlowDef
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBasePipeConversions

class ScoreJob(args: Args) extends JobBase(args) with
    HBasePipeConversions {

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
}
