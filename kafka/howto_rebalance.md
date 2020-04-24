
## Rebalance Storage Between Brokers (kafka-manager web)

For each topic you want to rebalance (eg, the large or high-throughput ones),
go to the topic page and do the blue "reassign partitions" button (or
potentially "generate" or "manual").

Monitor progress with the "Reassign Partitions" link at top of the page.

Finally, run a preferred replica election after partition movement is complete.

## Rebalance Storage Between Brokers (CLI)

For example, after adding or removing brokers from the cluster.

Create a list of topics to move, and put it in `/tmp/topics_to_move.json`:

    {
      "version": 1,
      "topics": [
        {"topic": "sandcrawler-shadow.grobid-output"},
        {"topic": "fatcat-prod.api-crossref"}
      ]
    }

On a kafka broker, go to `/srv/kafka-broker/kafka-*/bin`, generate a plan, then
inspect the output:

    ./kafka-reassign-partitions.sh --zookeeper localhost:2181 --broker-list "280,281,284,285,263" --topics-to-move-json-file /tmp/topics_to_move.json --generate > /tmp/reassignment-plan.json
    cat /tmp/reassignment-plan.json | rg '^\{' | tail -n1 > /tmp/new-plan.json
    cat /tmp/reassignment-plan.json | rg '^\{' | jq .

If that looks good, start the rebalance:

    ./kafka-reassign-partitions.sh --zookeeper localhost:2181 --reassignment-json-file /tmp/new-plan.json --execute

Then monitor progress:

    ./kafka-reassign-partitions.sh --zookeeper localhost:2181 --reassignment-json-file /tmp/new-plan.json --verify

Finally, run a preferred replica election after partition movement is complete.
Currently do this through the web interface (linked above).
