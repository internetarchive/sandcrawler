package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.Stat
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class GroupFatcatWorksSubsetJob(args: Args) extends JobBase(args) {

  val fatcatLhsRowCount = Stat("fatcat-rows-filtered-left", "sandcrawler")
  val fatcatRhsRowCount = Stat("fatcat-rows-filtered-right", "sandcrawler")
  val joinedRowCount = Stat("joined-rows", "sandcrawler")

  val fatcatScorableLhs : Scorable = new FatcatScorable()
  val fatcatPipeLhs : TypedPipe[(String, ReduceFeatures)] = fatcatScorableLhs
    .getInputPipe(args)
    .map { r =>
      fatcatLhsRowCount.inc
      r
    }

  val fatcatScorableRhs : Scorable = new FatcatScorableRight()
  val fatcatPipeRhs : TypedPipe[(String, ReduceFeatures)] = fatcatScorableRhs
    .getInputPipe(args)
    .map { r =>
      fatcatRhsRowCount.inc
      r
    }

  val joinedPipe = fatcatPipeLhs
    .addTrap(TypedTsv(args("output") + ".trapped"))
    .join(fatcatPipeRhs)

  // TypedTsv doesn't work over case classes.
  joinedPipe
    // filter out trivial self-matches (releases are identical)
    .filter { case (slug, (fatcatFeaturesLeft, fatcatFeaturesRight)) =>
      Scorable.selfMatchable(fatcatFeaturesLeft, fatcatFeaturesRight)
    }
    .map { case (slug, (fatcatFeaturesLeft, fatcatFeaturesRight)) =>
      joinedRowCount.inc
      new ReduceOutput(
        slug,
        Scorable.computeSimilarity(fatcatFeaturesLeft, fatcatFeaturesRight),
        fatcatFeaturesLeft.json,
        fatcatFeaturesRight.json)
    }
    .map { entry => (entry.slug, entry.score, entry.json1, entry.json2) }
    .write(TypedTsv[(String, Int, String, String)](args("output")))
}
