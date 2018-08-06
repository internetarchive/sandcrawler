import java.text.Normalizer

import scala.math
import scala.util.parsing.json.JSON

import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBasePipeConversions

class ScoreJob(args: Args, sc1 : Scorable, sc2 : Scorable) extends JobBase(args) with HBasePipeConversions {
  val pipe1 : TypedPipe[(String, ReduceFeatures)] = sc1.getInputPipe(args)
  val pipe2 : TypedPipe[(String, ReduceFeatures)] = sc2.getInputPipe(args)

  pipe1.join(pipe2).map { entry =>
    val (slug : String, (features1 : ReduceFeatures, features2 : ReduceFeatures)) = entry
    Scorable.computeOutput(features1, features2)
  }
    .write(TypedTsv[ReduceOutput](args("output")))
}
