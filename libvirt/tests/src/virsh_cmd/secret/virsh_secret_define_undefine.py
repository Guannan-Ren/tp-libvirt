import os
import tempfile
import commands
from autotest.client.shared import error
from virttest import virsh, data_dir

SECRET_DIR = "/etc/libvirt/secrets/"
SECRET_BASE64 = "c2VjcmV0X3Rlc3QK"

def run(test, params, env):
    """
    Test command: virsh secret-define <file>
                  secret-undefine <secret>
    The testcase is to define or modify a secret
    from an XML file, then undefine it
    """

    # MAIN TEST CODE ###
    # Process cartesian parameters
    status_error = ("yes" == params.get("status_error", "no"))
    secret_ref = params.get("secret_ref")
    ephemeral = params.get("ephemeral_value", "no")
    private = params.get("private_value", "no")

    if secret_ref == "secret_valid_uuid":
       # Generate valid uuid
        cmd = "uuidgen"
        status, uuid = commands.getstatusoutput(cmd)
        if status:
            raise error.TestNAError("Failed to generate valid uuid")

    elif secret_ref == "secret_invalid_uuid":
        uuid = params.get(secret_ref)

    # Get a full path of tmpfile, the tmpfile need not exist
    tmp_dir = data_dir.get_tmp_dir()
    volume_path = os.path.join(tmp_dir, "secret_volume")

    secret_xml = """
<secret ephemeral='%s' private='%s'>
  <uuid>%s</uuid>
  <usage type='volume'>
    <volume>%s</volume>
  </usage>
</secret>
""" % (ephemeral, private, uuid, volume_path)

    # Write secret xml into a tmpfile
    tmp_file = tempfile.NamedTemporaryFile(prefix=("secret_xml_"),
                                           dir=tmp_dir)
    xmlfile = tmp_file.name
    tmp_file.close()

    fd = open(xmlfile, 'w')
    fd.write(secret_xml)
    fd.close()

    # Run the test
    try:
        cmd_result = virsh.secret_define(xmlfile, debug=True)
        secret_define_status = cmd_result.exit_status

        # Check status_error
        if status_error and secret_define_status == 0:
            raise error.TestFail("Run successfully with wrong command!")
        elif not status_error and secret_define_status != 0:
            raise error.TestFail("Run failed with right command")

        if secret_define_status != 0:
            return

        # Check ephemeral attribute
        secret_obj_xmlfile = os.path.join(SECRET_DIR, uuid + ".xml")
        exist = os.path.exists(secret_obj_xmlfile)
        if (ephemeral == "yes" and exist) or \
           (ephemeral == "no" and not exist):
            raise error.TestFail("The ephemeral attribute worked not expected")

        # Check private attrbute
        virsh.secret_set_value(uuid, SECRET_BASE64, debug=True)
        cmd_result = virsh.secret_get_value(uuid, debug=True)
        status = cmd_result.exit_status
        if (private == "yes" and status == 0) or \
           (private == "no" and status != 0):
            raise error.TestFail("The private attribute worked not expected")

    finally:
        # cleanup
        if secret_define_status == 0:
            cmd_result = virsh.secret_undefine(uuid, debug=True)
            if cmd_result.exit_status != 0:
                raise error.TestFail("Failed to undefine secret object")

        if os.path.exists(xmlfile):
            os.remove(xmlfile)
