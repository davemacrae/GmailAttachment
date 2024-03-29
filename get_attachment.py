#!/usr/bin/python3

import pickle
import os
import sys
import base64
import argparse
import inspect
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient import errors

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://mail.google.com/"]

global PROGRAM_ARGS
MAX_INT = 2147483647  # to get around the 32/64 bit issue with sys.maxsize


def main():
    """
    Based on examples from: https://developers.google.com/gmail/api/quickstart/python
    Shows basic usage of the Gmail API.
    Find all unread messages with label "frame"
    Download any attachments to these messages
    mark the message as read by removing label "UNREAD"
    archive message by removing label "INBOX"
    """

    # get any command line arguments

    global PROGRAM_ARGS
    PROGRAM_ARGS = getargs()

    outputDir = PROGRAM_ARGS.output if PROGRAM_ARGS.output else "."
    outputDir = outputDir + "/"

    configDir = PROGRAM_ARGS.config if PROGRAM_ARGS.config else "."
    configDir = configDir + "/"

    label = PROGRAM_ARGS.label if PROGRAM_ARGS.label else "frame"

    service = build("gmail", "v1", credentials=login(configDir))
    labelID = get_labels(service, labelName=label)

    messages = get_messages(service, labelID, no_messages=PROGRAM_ARGS.limit)

    if not messages:
        if PROGRAM_ARGS.verbose:
            print("No unread messages found.")
    else:
        if PROGRAM_ARGS.verbose:
            print("Found", len(messages), "unread Message(s)")
        for message in messages:
            get_message_content(service, message["id"], outputDir)
            if PROGRAM_ARGS.delete:
                delete_message(service, message["id"])
            else:
                if PROGRAM_ARGS.trash:
                    trash_message(service, message["id"])
                else:
                    mark_message_read(service, message["id"])

    return


def login(config_dir):
    """
    The file "token.pickle" stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first
    time. credentials JSON file must exist.

    :param config_dir: Location of the configuration/credentials files
    """

    gmail_creds = None
    pickle_file = config_dir + "token.pickle"
    credentials_file = config_dir + "credentials.json"

    if not os.path.exists(credentials_file):
        print(f"Error: Cannot find credentials file {credentials_file}")
        exit(1)

    if os.path.exists(pickle_file):
        try:
            with open(pickle_file, "rb") as token:
                gmail_creds = pickle.load(token)
        except OSError as err:
            print("OS error: {0}".format(err))
            sys.exit(1)
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

# If there are no (valid) credentials available, let the user log in.
    if not gmail_creds or not gmail_creds.valid:
        if gmail_creds and gmail_creds.expired and gmail_creds.refresh_token:
            try:
                gmail_creds.refresh(Request())
            except OSError as err:
                print("OS error: {0}".format(err))
                sys.exit(1)
            except Exception:
                print("Unexpected error:", sys.exc_info()[0])
                raise
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                gmail_creds = flow.run_local_server(port=0)
            except OSError as err:
                print("OS error: {0}".format(err))
                sys.exit(1)
            except Exception:
                print("Unexpected error:", sys.exc_info()[0])
                raise

        # Save the credentials for the next run
        try:
            with open(pickle_file, "wb") as token:
                pickle.dump(gmail_creds, token)
        except OSError as err:
            print("OS error: {0}".format(err))
            sys.exit(1)
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    return gmail_creds


def get_labels(service, labelName=None):
    # Call the Gmail API

    """
    We want to get a list of all labels that are defined in our GMAIL account.
    When we get the list this includes the name of the label and the ID. It is the ID that we need for subsequent
    calls to the API.

    :param service: Authorized Gmail API service instance.
    :param labelName: the label that tags the messages we're interested in

    The function returns the ID of the required label.

    """
    results, labels, labelId = None, None, None

    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
    except errors.HttpError as error:
        print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)
        sys.exit(1)

    if not labels:
        if PROGRAM_ARGS.verbose:
            print("No labels found.")
    else:
        for label in labels:
            if label["name"] == labelName:
                labelId = label["id"]

    return labelId


def get_messages(service, label=None, no_messages=10000):
    """
    We want to get a list of all messages (defined by a specific label if required)
    We should also only get unread messages.

    :param service: Authorized Gmail API service instance.
    :param label: the label that tags the messages we're interested in
    :param no_messages: limit the number of messages retrieved to count

    """
    global PROGRAM_ARGS

    # Even if label is not specified, we want to only retrieve UNREAD messages
    # If "label" is not defined then we will retrieve all unread messages from the mailbox.
    # Implemented: need to determine if we want to retrieve all UNREAD messages (which is the
    # current behavior) or just those that haven't been archived.
    #  i.e. do we need to make INBOX part of the label list.

    if label is None:
        label = ["UNREAD", "INBOX"] if PROGRAM_ARGS.unread else ["UNREAD"]
    elif PROGRAM_ARGS.all:
        label = [label]
    else:
        label = [label, "UNREAD", "INBOX"] if PROGRAM_ARGS.unread else [label, "UNREAD"]

    messages = []

    try:
        """
        Loop through the messages in the GMAIL inbox. Gmail, by default, returns a maximum of 100 messages in a
        call with nextPageToken set to indicate that there are more messages. (Note that if the maxResults parameter
        is used, the lesser of maxResults and 500 messages are returned).

        The call that retrieves that last block will not have this set."""
        # get the initial set of messages (if any)
        if PROGRAM_ARGS.verbose:
            print(f"Retrieve a maximum of {no_messages} messages from GMAIL")

        # Need to make sure that we can retrieve 'limit' number of messages if 'limit' != None.

        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=label, pageToken=None, maxResults=no_messages)
            .execute()
        )

        messages.extend(results.get("messages", []))
        no_messages = no_messages - len(results.get("messages", []))

        while results.get("nextPageToken") and no_messages > 0:
            # if nextPageToken is set then there are more messages to retrieve.
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=label,
                    pageToken=results.get("nextPageToken"),
                    maxResults=no_messages,
                )
                .execute()
            )
            # extend the message list to include the new ones retrieved.
            messages.extend(results.get("messages", []))
            no_messages = no_messages - len(results.get("messages", []))

    except errors.HttpError as error:  # this is probably not the best solution
        print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)
        sys.exit(1)

    return messages


def get_message_content(service, msg_id, outputDir="./"):
    """
    Get and store attachment from Message with given id.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of Message containing attachment.
    :param outputDir:Directory for output
    """

    global PROGRAM_ARGS

    uid = "me"

    try:
        message = service.users().messages().get(userId=uid, id=msg_id).execute()

        try:
            for part in message["payload"]["parts"]:
                if part["filename"]:
                    if not PROGRAM_ARGS.dryrun:
                        if "data" in part["body"]:
                            data = part["body"]["data"]
                        else:
                            att_id = part["body"]["attachmentId"]
                            att = (
                                service.users()
                                .messages()
                                .attachments()
                                .get(userId=uid, messageId=msg_id, id=att_id)
                                .execute()
                            )
                            data = att["data"]
                        file_data = base64.urlsafe_b64decode(data.encode("UTF-8"))

                    # it appears that filename can contain non-safe characters like "/", i.e. it has a full path
                    # this appears to be because the UNIX mail command includes the full path of the
                    # attachment as given:
                    #   mail -A ~/PycharmPrProjects/frame/ACF1083.jpg frame@example.com
                    # we should do a basename on the filename to just get the bit we need.

                    path = outputDir + os.path.basename(part["filename"])
                    if PROGRAM_ARGS.verbose or PROGRAM_ARGS.dryrun:
                        print("Save File:", path)
                    if not PROGRAM_ARGS.dryrun:
                        try:
                            if PROGRAM_ARGS.noclobber:
                                # check if we should not overwrite
                                if os.path.exists(path):
                                    if PROGRAM_ARGS.verbose:
                                        print(f"Not overwriting {path}")
                                        continue
                            with open(path, "wb") as f:
                                f.write(file_data)
                        except OSError as err:
                            print("OS error: {0}".format(err))
                            sys.exit(1)
                        except Exception:
                            print("Unexpected error:", sys.exc_info()[0])
                            raise
        except KeyError:
            if PROGRAM_ARGS.verbose:
                print(f"Message {msg_id} didn't contain an attachment")

    except errors.HttpError as error:
        print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)
        sys.exit(1)


def mark_message_read(service, msg_id):
    """
    We now need to mark the message as read.
    This is done by removing the UNREAD label
    The message is also archived by removing the INBOX label.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of message to be altered
    """
    uid = "me"
    message = None

    if not PROGRAM_ARGS.dryrun:
        try:
            message = (
                service.users()
                .messages()
                .modify(userId=uid, id=msg_id, body={"removeLabelIds": ["UNREAD", "INBOX"]})
                .execute()
            )
        except errors.HttpError as error:
            print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)

        # need to check that the UNREAD label has been removed.

        labelIDs = message.get("labelIds")
        if "UNREAD" in labelIDs:
            print("Something went wrong, label UNREAD still there")
        else:
            if PROGRAM_ARGS.verbose:
                print(f"Message {msg_id} marked as Read")
    else:
        print(f"Message {msg_id} will be marked as Read")
    return


def delete_message(service, msg_id):
    """
    We now need to delete the message. Note that this will permanently and irretrievably delete the messages, it
    can't be recovered.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of message to be altered
    """
    uid = "me"

    if not PROGRAM_ARGS.dryrun:
        try:
            service.users().messages().delete(userId=uid, id=msg_id).execute()
        except errors.HttpError as error:
            print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)

    return


def trash_message(service, msg_id):
    """
    We now need to move the message to trash

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of message to be altered
    """
    uid = "me"

    if not PROGRAM_ARGS.dryrun:
        try:
            service.users().messages().trash(userId=uid, id=msg_id).execute()
        except errors.HttpError as error:
            print(f"An error occurred in {inspect.stack()[0][3]}: %s" % error)
    else:
        print(f"Will Trash {msg_id}")

    return


def getargs():
    """
    We now need to parse the arguments list.
    """

    parser = argparse.ArgumentParser(
        description="This application downloads attachments from a GMAIL account "
                    + "Copyright 2021 Dave MacRae dave@macrae.org.uk"
    )

    parser.add_argument(
        "--output", "-o", type=str, help="Specify the target directory for downloads"
    )
    parser.add_argument(
        "--config", type=str, help="Specify the directory containing config files"
    )
    parser.add_argument(
        "--label", type=str, help="Specify the target label for getting messages"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=MAX_INT,
        help="limit the number of attachments downloaded",
    )
    parser.add_argument(
        "--count",
        "-c",
        action="store_true",
        help="Just calculate number of available messages and exit",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete messages at GMAIL rather than just archive",
    )
    parser.add_argument(
        "--trash",
        action="store_true",
        help="Trash messages at GMAIL rather than just archive",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Don't actually do anything, just print out actions",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--unread",
        "-u",
        action="store_true",
        help="Only get unread messages from inbox, default is to get all undread messages even if archived",
    )
    parser.add_argument(
        "--noclobber", action="store_true", help="Don't overwrite existing files"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Get all messages irrespective of state. Helpful if you've sent yourself the "
             "message.",
    )

    args = parser.parse_args()

    # If "--output" is used and
    # the selected output directory is a directory
    # and the directory is writable
    if (
            args.output
            and not os.path.isdir(args.output)
            and not os.access(args.output, os.W_OK | os.X_OK)
    ):
        parser.error(f"Specified Output directory '{args.output}' does not exists")
    if (
            args.config
            and not os.path.isdir(args.config)
            and not os.access(args.config, os.R_OK)
    ):
        parser.error(f"Specified Config directory '{args.config}' does not exists")

    return args


if __name__ == "__main__":
    #
    # DONE:
    #   output folder
    #   Need to have some kind of argument parsing
    #   verbose level
    #   do we want to limit the number of messages retrieved
    #   do we want to overwrite existing files
    #   do we want to delete the read messages rather than just archiving them
    #   do we want an option to flag what label we want to use for the attachments

    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(1)
        except SystemExit:
            # noinspection PyProtectedMember
            os._exit(1)
    sys.exit(0)
