package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.Stat
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class ScoreJob(args: Args) extends JobBase(args) {

  val grobidRowCount = Stat("grobid-rows-filtered", "sandcrawler")
  val crossrefRowCount = Stat("crossref-rows-filtered", "sandcrawler")
  val joinedRowCount = Stat("joined-rows", "sandcrawler")
  /* TODO:
  val uniqueDoiCount = Stat("unique-doi-count", "sandcrawler")
  val uniqueSha1Count = Stat("unique-sha1-count", "sandcrawler")
  */

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

  val joinedPipe = grobidPipe
    .addTrap(TypedTsv(args("output") + ".trapped"))
    .join(crossrefPipe)

  /* TODO:
  // Reduces to count unique SHA1 and DOI
  joinedPipe
    .map { case (_, (grobidFeatures, _)) => grobidFeatures.sha }
    .distinct
    .map { _ => uniqueSha1Count.inc }
  joinedPipe
    .map { case (_, (_, crossrefFeatures)) => crossrefFeatures.doi }
    .distinct
    .map { _ => uniqueDoiCount.inc }
  */

  // TypedTsv doesn't work over case classes.
  joinedPipe
    .map { case (slug, (grobidFeatures, crossrefFeatures)) =>
      joinedRowCount.inc
      //val (slug : String, (grobidFeatures: ReduceFeatures, crossrefFeatures: ReduceFeatures)) = entry
      new ReduceOutput(
        slug,
        Scorable.computeSimilarity(grobidFeatures, crossrefFeatures),
        grobidFeatures.json,
        crossrefFeatures.json)
    }
    .map { entry => (entry.slug, entry.score, entry.json1, entry.json2) }
    .write(TypedTsv[(String, Int, String, String)](args("output")))
}
