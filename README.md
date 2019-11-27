# VirtualBIRD

Tool to create virtual networks using BIRD!

## How to use
See example.yaml for configuration, then run:
```shell script
sudo virtualbird example.yaml
```

### This is how you use the environment

Running a bird command:
```shell script
sudo birdc -s /tmp/vb_r1.sock <bird command>
```

Running a command in a router:
```shell script
sudo ip netns exec vb_r1 <command>
```

## How to install
Clone, then:
```shell script
sudo pip install .
```

