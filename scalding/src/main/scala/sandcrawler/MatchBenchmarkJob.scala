package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class MatchBenchmarkJob(args: Args) extends JobBase(args) {
  // TODO: Instantiate any subclass of Scorable specified in args.
  val sc1 : Scorable = new BibjsonScorable()
  val sc2 : Scorable = new BibjsonScorable()
  val leftArgs = args + ("bibjson-input" -> List(args("left-bibjson")))
  val rightArgs = args + ("bibjson-input" -> List(args("right-bibjson")))
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(leftArgs)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = sc2.getInputPipe(rightArgs)

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
