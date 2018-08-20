package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class ScoreJob(args: Args) extends JobBase(args) {
  // TODO: Instantiate any subclass of Scorable specified in args.
  val sc1 : Scorable = new GrobidScorable()
  val sc2 : Scorable = new CrossrefScorable()
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(args)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = sc2.getInputPipe(args)

  pipe1
    .addTrap(TypedTsv(args("output") + ".trapped"))
    .join(pipe2)
    .map { entry =>
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

/*
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
 */
