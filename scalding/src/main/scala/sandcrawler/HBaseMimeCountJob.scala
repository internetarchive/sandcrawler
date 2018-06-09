package sandcrawler

import com.twitter.scalding.Args

class HBaseMimeCountJob(args: Args) extends HBaseCountJob(args, "file:mime") {}

