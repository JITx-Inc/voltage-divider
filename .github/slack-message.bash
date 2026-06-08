#!/bin/bash
set -Eeuo pipefail

# Required env var inputs
if [ ! -v SLACK_TOKEN ] ; then
  echo "Error: Environment variable SLACK_TOKEN not found"
  exit -1
fi

if [ $# == 0 ] ; then
  echo "usage: $0 [-q] [-u GitHubUser | -e user@example.com | -c software-team | -s C04E41FMKLY | -f file.txt | -j payload.json ] Message..."
  exit -1
fi

### Channels
declare -A CHANNELS=(
  [concourse-ci]=C04E41FMKLY
  [concourse-ci-dev]=C04D7P98MUN
  [dev-ops]=C02A219RYCA
  [general]=CKVST5V9T
  [jitpcb]=CKY4541KQ
  [software-team]=C02G1SYU3CY
  )

### GitHub Userids
declare -A GITHUBUSERS=(
  [AashnaP22]=U051BRA3004
  [alijitx]=U04UHTDRV1Q
  [APagin]=U01N3QH9YUV
  [ariel-hi]=U011XGLJ0P3
  [bhusang]=U02HGEN8C2W
  [callendorph]=U05G0TT5TJ7
  [CuppoJava]=UKVSTQ072
  [d-haldane]=UKJEB361Y
  [emspin]=U04RHJJC96E
  [erwin-lau]=U03L6R79GHH
  [falstjit]=U03MK0F22CB
  [fgreen]=U02T3NS9085
  [jackbackrack]=UKJGB59GB
  [JMahal-JITX]=U05LFG8GZ50
  [jwatson0]=U038G096K1N
  [lchao-jitx]=U03PUQFSH4M
  [PhilippeFerreiraDeSousa]=U011LCS99T8
  [plasmajitx]=U027GSC8WG1
  [shanagr]=U04RXPDU895
  [tenbillionwords]=U027GSC8WG1
  [the-eigengrau]=U02U52N1JE7
  [tjknoth]=U056HDTTPT5
  )

### Emails
declare -A EMAILS=(
  [a.hirschberg@jitx.com]=${GITHUBUSERS[ariel-hi]}
  [a.li@jitx.com]=${GITHUBUSERS[alijitx]}
  [bgupta@thronax.com]=${GITHUBUSERS[bhusang]}
  [c.allendorph@jitx.com]=${GITHUBUSERS[callendorph]}
  [ci@jitx.com]=${CHANNELS[concourse-ci]}
  [d.haldane@jitx.com]=${GITHUBUSERS[d-haldane]}
  [e.lau@jitx.com]=${GITHUBUSERS[erwin-lau]}
  [f.alstromer@jitx.com]=${GITHUBUSERS[falstjit]}
  [f.green@jitx.com]=${GITHUBUSERS[fgreen]}
  [hirschberg.ariel@gmail.com]=${GITHUBUSERS[ariel-hi]}
  [j.watson@jitx.com]=${GITHUBUSERS[jwatson0]}
  [l.chao@jitx.com]=${GITHUBUSERS[lchao-jitx]}
  [p.li@jitx.com]=${GITHUBUSERS[CuppoJava]}
  [philippe.fdesousa@gmail.com]=${GITHUBUSERS[PhilippeFerreiraDeSousa]}
  [s.agarwal@jitx.com]=${GITHUBUSERS[shanagr]}
  [s.messick@jitx.com]=${GITHUBUSERS[plasmajitx]}
  [107752351+erwin-lau@users.noreply.github.com]=${GITHUBUSERS[erwin-lau]}
  [109105658+falstjit@users.noreply.github.com]=${GITHUBUSERS[falstjit]}
  [109628339+lchao-jitx@users.noreply.github.com]=${GITHUBUSERS[lchao-jitx]}
  [128093458+alijitx@users.noreply.github.com]=${GITHUBUSERS[alijitx]}
  [31138886+d-haldane@users.noreply.github.com]=${GITHUBUSERS[d-haldane]}
  [57466867+tenbillionwords@users.noreply.github.com]=${GITHUBUSERS[plasmajitx]}
  [83436214+jitxcicd@users.noreply.github.com]=${CHANNELS[concourse-ci]}
  )

SLACK_POST_MESSAGE_URL="https://slack.com/api/chat.postMessage"
SLACK_GET_UPLOAD_URL="https://slack.com/api/files.getUploadURLExternal"
SLACK_COMPLETE_UPLOAD_URL="https://slack.com/api/files.completeUploadExternal"
CHANNEL=""
QUIET=false
EXTRAMESSAGE=""
ATTACHFILE=""
JSONFILE=""

# command-line args
while [[ $# -gt 0 && "${1:0:1}" == "-" ]] ; do
  case "${1}" in
    # GitHub username
    -u) if [ -v GITHUBUSERS[${2}] ] ; then
          CHANNEL="${GITHUBUSERS[${2}]}"
        else
          EXTRAMESSAGE="GitHub user \"${2}\" not configured in $(basename ${0})"
        fi
        shift 2
        ;;
    # email
    -e) if [ -v EMAILS[${2}] ] ; then
          CHANNEL="${EMAILS[${2}]}"
        else
          EXTRAMESSAGE="Email \"${2}\" not configured in $(basename ${0})"
        fi
        shift 2
        ;;
    # Slack channel name
    -c) if [ -v CHANNELS[${2}] ]; then
          CHANNEL="${CHANNELS[${2}]}"
        else
          EXTRAMESSAGE="Channel \"${2}\" not configured in $(basename ${0})"
        fi
        shift 2
        ;;
    # Slack channel address (like "C04E41FMKLY")
    -s) CHANNEL="${2}"
        shift 2
        ;;
    # Quiet
    -q) QUIET=true
        shift
        ;;
    # File attachment
    -f) ATTACHFILE="${2}"
        shift 2
        if [ ! -e ${ATTACHFILE} ] ; then
            echo "ERROR: Attachment file \"${ATTACHFILE}\" does not exist"
            exit -1
        fi
        ;;
    # JSON Payload
    -j) JSONFILE="${2}"
        shift 2
        if [ ! -e ${JSONFILE} ] ; then
            echo "ERROR: JSON payload file \"${JSONFILE}\" does not exist"
            exit -1
        fi
        ;;
    # else
    *)  echo "Unrecognized arg: ${1}"
        exit -1
        ;;
  esac
done

# any remaining args are the message
MESSAGE="$*"
[ "${EXTRAMESSAGE}" != "" ] && MESSAGE="${MESSAGE}"$'\n'"($EXTRAMESSAGE)"

# file attachment overrides preformatted json sending
if [ "${ATTACHFILE}" != "" ] ; then
  # upload ATTACHFILE as a text snippet

  # get base filename
  FILENAME=$(basename "${ATTACHFILE}")

  [ "${QUIET}" != "true" ] && echo "Uploading \"${FILENAME}\" with message \"${MESSAGE}\" to channel ${CHANNEL}"

  # get file length
  FLEN=$(wc -c "${ATTACHFILE}" | awk '{print $1}')

  # retrieve upload url from slack
  URLDATA=$(curl -s --get \
                 -H "Authorization: Bearer ${SLACK_TOKEN}" \
                 --data filename="${FILENAME}" \
                 --data length="${FLEN}" \
                 "${SLACK_GET_UPLOAD_URL}")
  if [ "$(echo ${URLDATA} | jq -r .ok)" == "true" ] ; then
    # extract upload url from response
    UPLOAD_URL=$(echo ${URLDATA} | jq -r .upload_url)
    FILE_ID=$(echo ${URLDATA} | jq -r .file_id)
  else
    echo "Error: $(echo ${URLDATA} | jq -r .error)"
    exit 1
  fi
  # upload the file to the given upload url
  curl -s --fail -X POST \
       -F filename="@${ATTACHFILE}" \
       "${UPLOAD_URL}" > /dev/null
  # complete the upload
  OUTPUT=$(curl -s -X POST \
                -H "Authorization: Bearer ${SLACK_TOKEN}" \
                --data files="[{\"id\": \"${FILE_ID}\"}]" \
                --data channel_id="${CHANNEL}" \
                --data initial_comment="${MESSAGE}" \
                "${SLACK_COMPLETE_UPLOAD_URL}")
else
  # send MESSAGE or JSONFILE as chat.postMessage

  # if preconfigured JSONFILE was not specified
  if [ "${JSONFILE}" == "" ] ; then
      # Create temp file with slack json content
      JSONFILE=`mktemp -p .`
      jq -cn \
         --arg channel "${CHANNEL}" \
         --arg text "${MESSAGE}" \
         '.channel=$channel|.text=$text' \
         > "${JSONFILE}"
  elif [ "${CHANNEL}" != "" ] ; then
      # both JSONFILE and CHANNEL specified
      JSONFILEORIG="${JSONFILE}"
      JSONFILE=`mktemp -p .`
      # update the channel in the given json file
      jq -c \
         ". | .channel=\"${CHANNEL}\"" \
         < "${JSONFILEORIG}" \
         > "${JSONFILE}"
  fi

  # take whatever is in JSONFILE and post it to slack
  OUTPUT=$(curl -s -X POST "${SLACK_POST_MESSAGE_URL}" \
       -H "Accept: application/json" \
       -H "Content-type: application/json; charset=utf-8" \
       -H "Authorization: Bearer ${SLACK_TOKEN}" \
       -d @- \
       < "${JSONFILE}")
fi
# check results
if [ "$(echo ${OUTPUT} | jq -r .ok)" == "true" ] ; then
  [ "${QUIET}" != "true" ] && echo "ok"
  exit 0
else
  echo "Error: $(echo ${OUTPUT} | jq -r .error)"
  exit 1
fi

