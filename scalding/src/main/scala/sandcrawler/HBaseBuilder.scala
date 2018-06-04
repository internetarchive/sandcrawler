package sandcrawler

import cascading.tuple.Fields
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBaseSource
import scala._

object HBaseBuilder {
  // map from column families to column names
  val schema = Map("f" -> List("c"),
    "file" -> List("size", "mime", "cdx"),
    "grobid0" -> List("status_code", "quality", "status", "tei_xml", "tei_json", "metadata"),
    "match0" -> List("status", "doi", "info"))
  // map from colFamily:colName -> colFamily
  // Code from https://stackoverflow.com/a/50595189/6310511
  val inverseSchema = for ((k, vs) <- schema; v <- vs) yield (k + ":" + v, k)

  // The argument should be a string with a comma-separated list of family:column, 
  // such as "f:c, file:size". Spaces after the comma are optional.
  @throws(classOf[IllegalArgumentException])
  def parseColSpec(colSpec: String) : (List[String], List[Fields]) = {
    val colSpecs = (if (colSpec.trim.length == 0) List() else colSpec.split(", *").toList)

    // Verify that all column specifiers are legal.
    for (colSpec <- colSpecs) {
      if (!(inverseSchema contains colSpec)) {
        throw new IllegalArgumentException("No such column: " + colSpec)
      }
      val pair = colSpec split(":")
      if (colSpec.split(":").length != 2) {
        throw new IllegalArgumentException("Bad column specifier " + colSpec + 
          " (specifiers should be family:name)")
      }
    }

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

  def build(table: String, server: String, colSpec: String, sourceMode: SourceMode, keyList: List[String] = List("key")) = {
    val (families, fields) = parseColSpec(colSpec)
    new HBaseSource(table, server, new Fields("key"), families, fields, sourceMode = sourceMode, keyList = keyList)
  }
}
