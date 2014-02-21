import os
import re
import commands
import logging
import tempfile
from autotest.client.shared import error
from virttest import virsh, data_dir

def run(test, params, env):
    """
    Test command: virsh secret-list

    Returns a list of secrets
    """

    # MAIN TEST CODE ###
    # Process cartesian parameters
    status_error = ("yes" == params.get("status_error", "no"))
    secret_list_option = params.get("secret_list_option", "")

    # Generate valid uuid
    cmd = "uuidgen"
    status, uuid = commands.getstatusoutput(cmd)
    if status:
        raise error.TestNAError("Failed to generate valid uuid")

    # Get a full path of tmpfile, the tmpfile need not exist
    tmp_dir = data_dir.get_tmp_dir()
    volume_path = os.path.join(tmp_dir, "secret_volume")

    secret_xml = """
<secret ephemeral='no' private='yes'>
  <uuid>%s</uuid>
  <usage type='volume'>
    <volume>%s</volume>
  </usage>
</secret>
""" % (uuid, volume_path)

    # Write secret xml into a tmpfile
    tmp_file = tempfile.NamedTemporaryFile(prefix=("secret_xml_"),
                                           dir=tmp_dir)
    xmlfile = tmp_file.name
    tmp_file.close()

    fd = open(xmlfile, 'w')
    fd.write(secret_xml)
    fd.close()

    try:
        virsh.secret_define(xmlfile, debug=True)

        cmd_result = virsh.secret_list(secret_list_option, debug=True)
        output = cmd_result.stdout.strip()
        exit_status = cmd_result.exit_status
        if not status_error and exit_status != 0:
            raise error.TestFail("Run failed with right command")
        if status_error and exit_status == 0:
            raise error.TestFail("Run successfully with wrong command!")

        # Reture if secret-list failed
        if exit_status != 0:
            return

        # Check the result
        match_string = "%s" % uuid
        m = re.search(match_string, output)
        if secret_list_option == "" or \
            secret_list_option == "--no-ephemeral" or \
            secret_list_option == "--private":
            if not m:
                raise error.TestFail("Failed list secret object %s" % uuid)
        elif secret_list_option == "--ephemeral" or \
            secret_list_option == "--no-private":
            if m:
                raise error.TestFail("Secret object %s shouldn't be listed out"
                                     % uuid)
        else:
            raise error.TestFail("Unknow secret-list option")
    finally:
        #Cleanup
        virsh.secret_undefine(uuid, debug=True)

        if os.path.exists(xmlfile):
            os.remove(xmlfile)
