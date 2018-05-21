
package example

import com.twitter.scalding._

object WordCountJob {

  def main(args: Array[String]) {
    (new WordCountJob(Args(List("--local", "", "--input", "dummy.txt", "--output", "dummy-out.txt")))).run

    import io.Source
    for (line <- Source.fromFile("dummy-out.txt").getLines())
      println(line)
  }
}

class WordCountJob(args : Args) extends Job(args) {
  TypedPipe.from(TextLine(args("input")))
    .flatMap { line => line.split("""\s+""") }
    .groupBy { word => word }
    .size
    .write(TypedTsv(args("output")))
}
