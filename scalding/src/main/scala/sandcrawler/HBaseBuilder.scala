package sandcrawler

import scala._

import cascading.tap.SinkMode
import cascading.tuple.Fields
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBaseSource

object HBaseBuilder {
  // map from column families to column names
  val schema = Map("f" -> List("c"),
    "file" -> List("size", "mime", "cdx"),
    "grobid0" -> List("status_code", "quality", "status", "tei_xml", "tei_json", "metadata"),
    "match0" -> List("status", "doi", "info"))
  val inverseSchema = {for ((k,vs) <- schema; v <-vs) yield (k + ":" + v)}.toList

  // The argument should be of the form family:column, such as "file:size".
  @throws(classOf[IllegalArgumentException])
  def parseColSpec(colSpec: String) {
    if (!(inverseSchema contains colSpec)) {
      throw new IllegalArgumentException("No such column: " + colSpec)
    }
    val pair = colSpec split(":")
    if (pair.length != 2) {
      throw new IllegalArgumentException("Bad column specifier " + colSpec +
        " (specifiers should be family:name)")
    }
    (pair(0), pair(1))
  }

  // The argument should be a comma-separated list of family:column, such as "f:c, file:size".
  @throws(classOf[IllegalArgumentException])
  def parseColSpecs(colSpecs: List[String]) : (List[String], List[Fields]) = {
    // Verify that all column specifiers are legal.
    for (colSpec <- colSpecs) parseColSpec(colSpec)

    // Produce and return a tuple containing:
    // 1. A list of column families.
    // 2. A corresponding list of Fields, each containing column names.
    val groupMap: Map[String, List[String]] = colSpecs.groupBy(c => (c split ":")(0))
    val families = groupMap.keys.toList
    val groupedColNames : List[List[String]] = families map {fam => {
      val cols = {groupMap(fam).map(v => v.split(":")(1))}
      cols}}
    (families, groupedColNames.map({fields => new Fields(fields : _*)}))
  }

  def build(table: String, server: String, colSpecs: List[String], sourceMode: SourceMode, keyList: List[String] = List("key")) : HBaseSource = {
    val (families, fields) = parseColSpecs(colSpecs)
    new HBaseSource(table, server, new Fields("key"), families, fields, sourceMode = sourceMode, keyList = keyList)
  }

  def buildSink(table: String, server: String, colSpecs: List[String], sinkMode: SinkMode, keyList: List[String] = List("key")) : HBaseSource = {
    val (families, fields) = parseColSpecs(colSpecs)
    new HBaseSource(table, server, new Fields("key"), families, fields, sinkMode = sinkMode)
  }
}
