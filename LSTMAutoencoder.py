import tensorflow as tf
from tf.nn.rnn_cell import LSTMCell
import numpy as np


class LSTMAutoencoder(object):

    """Basic version of LSTM-autoencoder.
  (cf. http://arxiv.org/abs/1502.04681)

  Usage:
    ae = LSTMAutoencoder(hidden_num, inputs)
    sess.run(ae.train)
  """

    def __init__(
        self,
        hidden_num,
        inputs,
        cell=None,
        optimizer=None,
        reverse=True,
        decode_without_input=False,
        ):
        """
    Args:
      hidden_num : number of hidden elements of each LSTM unit.
      inputs : a list of input tensors with size 
              (batch_num x elem_num), every item in this list is a tensor of data in one time slice, listed by time sequence
      cell : an rnn cell object (the default option 
            is `tf.python.ops.rnn_cell.LSTMCell`)
      optimizer : optimizer for rnn (the default option is
              `tf.train.AdamOptimizer`)
      reverse : Option to decode in reverse order.
      decode_without_input : Option to decode without input.
    """

        self.batch_num = inputs[0].get_shape().as_list()[0] #should be the number of instances in a batch
        self.elem_num = inputs[0].get_shape().as_list()[1]  #should be the dimension of a instance

        #create layer with hidden_num lstm neurons, if the layer has not been given  
        if cell is None:
            self._enc_cell = LSTMCell(hidden_num)
            self._dec_cell = LSTMCell(hidden_num)
        else:
            self._enc_cell = cell
            self._dec_cell = cell

        with tf.variable_scope('encoder'): # used for drawing tensorboard
            (self.z_codes, self.enc_state) = tf.nn.static_rnn(self._enc_cell, inputs, dtype=tf.float32)

        with tf.variable_scope('decoder') as vs:
            dec_weight_ = tf.Variable(tf.truncated_normal([hidden_num,
                    self.elem_num], dtype=tf.float32), name='dec_weight')
            dec_bias_ = tf.Variable(tf.constant(0.1,
                                    shape=[self.elem_num],
                                    dtype=tf.float32), name='dec_bias')

            if decode_without_input: # non-symmetric model
                dec_inputs = [tf.zeros(tf.shape(inputs[0]),
                              dtype=tf.float32) for _ in
                              range(len(inputs))]
                (dec_outputs, dec_state) = tf.contrib.rnn.static_rnn(self._dec_cell, dec_inputs, initial_state=self.enc_state,
                        dtype=tf.float32)
                if reverse:
                    dec_outputs = dec_outputs[::-1]
                dec_output_ = tf.transpose(tf.stack(dec_outputs), [1, 0,
                        2])
                dec_weight_ = tf.tile(tf.expand_dims(dec_weight_, 0),
                        [self.batch_num, 1, 1])
                self.output_ = tf.matmul(dec_output_, dec_weight_) + dec_bias_
            else:

                dec_state = self.enc_state # symmetric model
                dec_input_ = tf.zeros(tf.shape(inputs[0]),# data shape in this special batch
                        dtype=tf.float32)
                dec_outputs = []
                for step in range(len(inputs)): #inputs is a list of (batch_num x elem_num) items
                    if step > 0: # why should this be <0??
                        vs.reuse_variables() # name of predefined variable scope
                    (dec_input_, dec_state) = \
                        self._dec_cell(dec_input_, dec_state)
                    dec_input_ = tf.matmul(dec_input_, dec_weight_) \
                        + dec_bias_
                    dec_outputs.append(dec_input_)
                if reverse:
                    dec_outputs = dec_outputs[::-1] #reverse
                self.output_ = tf.transpose(tf.stack(dec_outputs), [1,
                        0, 2]) # permutate tensor dimension from [a,b,c] to [b, a, c]

        self.input_ = tf.transpose(tf.stack(inputs), [1, 0, 2]) # make the input output dimensions equal 
        self.loss = tf.reduce_mean(tf.square(self.input_
                                   - self.output_))

        if optimizer is None:
            self.train = tf.train.AdamOptimizer().minimize(self.loss)
        else:
            self.train = optimizer.minimize(self.loss)
