# -*- coding: utf-8 -*-
"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 10, 2015

@author: jrm
"""
import asyncio

from declaracad.core.api import Plugin


def patch_ipykernel():
    from ipykernel.inprocess.client import InProcessKernelClient

    def _dispatch_to_kernel(self, msg):
        """Send a message to the kernel and handle a reply."""
        kernel = self.kernel
        if kernel is None:
            msg = "Cannot send request. No kernel exists."
            raise RuntimeError(msg)

        stream = kernel.shell_stream
        self.session.send(stream, msg)
        msg_parts = stream.recv_multipart()
        # Already in an event loop
        # if run_sync is not None:
        #     dispatch_shell = run_sync(kernel.dispatch_shell)
        #     dispatch_shell(msg_parts)
        # else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(kernel.dispatch_shell(msg_parts))
        idents, reply_msg = self.session.recv(stream, copy=False)
        self.shell_channel.call_handlers_later(reply_msg)

    InProcessKernelClient._dispatch_to_kernel = _dispatch_to_kernel


class ConsolePlugin(Plugin):
    def start(self):
        patch_ipykernel()
