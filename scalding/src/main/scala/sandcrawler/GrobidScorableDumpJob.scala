
package sandcrawler

import cascading.pipe.Pipe
import com.twitter.scalding.Args
import com.twitter.scalding.TypedPipe
import com.twitter.scalding.TypedTsv
import parallelai.spyglass.base.JobBase

class GrobidScorableDumpJob(args: Args) extends JobBase(args) {

  val sc1 : Scorable = new GrobidScorable()
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(args)

  pipe1
    .map { case (slug, features) => (slug, features.json) }
    .write(TypedTsv[(String, String)](args("output")))
}
