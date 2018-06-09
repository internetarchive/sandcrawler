package sandcrawler

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import java.util.Properties
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class HBaseMimeCountJob(args: Args) extends HBaseCountJob(args, "file:mime") {}

