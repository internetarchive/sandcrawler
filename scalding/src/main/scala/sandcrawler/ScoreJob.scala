package sandcrawler

import cascading.flow.FlowDef
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBasePipeConversions

class ScoreJob(args: Args) extends JobBase(args) with
    HBasePipeConversions {

  val pipe1 : TypedPipe[(String, ReduceFeatures)] = ScoreJob.getScorable1().getInputPipe(args)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = ScoreJob.getScorable2().getInputPipe(args)

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
