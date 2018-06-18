package sandcrawler

import com.twitter.scalding.Args

class HBaseStatusCountJob(args: Args) extends HBaseCountJob(args, "grobid0:status_code")
