{
  "channel": $channel,
  "attachments": [
    {
      "color": $color,
      "blocks": [
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": $emoji
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " \n\n *\($desc)* \n\n \($branch) \($ver) \n\n"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " <\($url)|\($desc)>"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " \($ghlogtype)"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " \($ghlogtest)"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " \($ghlogbuild)"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": " \($ghlogpublish)"
          }
        }
      ]
    }
  ]
}

