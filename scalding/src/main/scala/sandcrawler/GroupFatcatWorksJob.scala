package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.Stat
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class GroupFatcatWorksJob(args: Args) extends JobBase(args) {

  val fatcatRowCount = Stat("fatcat-rows-filtered", "sandcrawler")
  val joinedRowCount = Stat("joined-rows", "sandcrawler")

  val fatcatScorable : Scorable = new FatcatScorable()
  val fatcatPipe : TypedPipe[(String, ReduceFeatures)] = fatcatScorable
    .getInputPipe(args)
    .map { r =>
      fatcatRowCount.inc
      r
    }

  val joinedPipe = fatcatPipe
    .addTrap(TypedTsv(args("output") + ".trapped"))
    .join(fatcatPipe)

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
