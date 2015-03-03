
import pygame
from components import BehaviorScript
from util_math import Vector2

from systems import PhysicsSystem

from copy import copy


class CameraFollow(BehaviorScript):

    def __init__(self, script_name, target_transform, cam_width, cam_height):
        super(CameraFollow, self).__init__(script_name)
        self.target_transform = target_transform
        self.width = cam_width
        self.height = cam_height

    def update(self):

        # center the target transform in the middle of the camera
        x = self.target_transform.position.x - self.width/2
        y = self.target_transform.position.y - self.height/2

        world = self.entity.world

        # keep camera within world bounds
        if world.is_bounded():
            if x < world.origin.x:
                x = world.origin.x

            elif x > world.origin.x + world.width - self.width:
                x = world.origin.x + world.width - self.width

            if y < world.origin.y:
                y = world.origin.y

            elif y > world.origin.y + world.height - self.height:
                y = world.origin.y + world.height - self.height

        # set the camera position accordingly
        self.entity.transform.position = Vector2(x, y)


class ElevatorPlatMovement(BehaviorScript):

    def __init__(self, spawn_point, script_name):
        super(ElevatorPlatMovement, self).__init__(script_name)

        self.velocity = Vector2(0, -100)
        self.spawn_point = spawn_point

    def update(self):
        dt = self.entity.world.engine.delta_time
        transform = self.entity.transform
        transform.position += self.velocity * dt

    def collision_event(self, other_collider):

        # reset to the bottom
        if other_collider.entity.tag == "ceiling":
            self.entity.transform.position.x = self.spawn_point.x
            self.entity.transform.position.y = self.spawn_point.y


# # add movement to a platform but have it ignore physical properties
# class PlatformMovement(BehaviorScript):
#
#     def __init__(self, script_name):
#         super(PlatformMovement, self).__init__(script_name)
#         self.h_speed = 100
#         self.velocity = Vector2(self.h_speed, 0)
#
#     # implement custom movement without rigid
#     def update(self):
#         dt = self.entity.world.engine.delta_time
#         transform = self.entity.transform
#         transform.position += self.velocity * dt
#
#         w = self.entity.collider.box.width
#
#         right_limit = 2000
#         left_limit = 800
#
#         right = transform.position.x + w/2
#         left = transform.position.x - w/2
#
#         if right > right_limit:
#             delta = right - right_limit
#             transform.position.x -= delta
#
#             self.velocity.x *= -1
#
#         elif left < left_limit:
#             delta = left_limit - left
#             transform.position.x += delta
#
#             self.velocity *= -1
#
#     def collision_event(self, other_collider):
#
#         # have the player go along with the platform
#         if other_collider.entity.name == "player":
#             other_collider.entity.rigid_body.velocity.x = self.velocity.x
#
#             # apply friction sliding ???


# This script defines the behavior of how the player moves in a 2d side scroller world
class PlayerPlatformMovement(BehaviorScript):

    def __init__(self, script_name):
        super(PlayerPlatformMovement, self).__init__(script_name)
        self.h_speed = 240
        self.v_speed = 350
        self.moving = False

        self.grounded = False
        self.holding_crate = False

    def update(self):
        keys = pygame.key.get_pressed()

        velocity = self.entity.rigid_body.velocity

        self.test_if_grounded()

        if self.grounded:

            x_scale = self.entity.transform.scale.x
            y_scale = self.entity.transform.scale.y

            # move left
            if keys[pygame.K_a]:
                self.moving = True
                velocity.x = -self.h_speed

                # fix the orientation of the transform based on the key press
                if x_scale > 0:
                    self.entity.transform.scale_by(-x_scale, y_scale)

            # move right
            elif keys[pygame.K_d]:
                self.moving = True
                velocity.x = self.h_speed

                if x_scale < 0:
                    self.entity.transform.scale_by(-x_scale, y_scale)

            if keys[pygame.K_LCTRL]:
                self.holding_crate = True
            else:
                self.holding_crate = False

            # test to see if the player wants to move a crate
            if keys[pygame.K_LCTRL]:

                # make sure the player is near a crate
                result = self.check_if_near_crate()
                if result[0]:
                    crate = result[1]
                    crate.rigid_body.velocity.x = self.entity.rigid_body.velocity.x

        if self.entity.get_script("player climb").climbing:

            if keys[pygame.K_a]:
                self.moving = True
                velocity.x = -self.h_speed/2

            elif keys[pygame.K_d]:
                self.moving = True
                velocity.x = self.h_speed/2
            else:
                velocity.x = 0

    def take_input(self, event):
        if event.type == pygame.KEYDOWN:
            x_scale = self.entity.transform.scale.x
            y_scale = self.entity.transform.scale.y

            # change orientation of the transform based on where the player is facing.
            if self.grounded:
                # turn left
                if event.key == pygame.K_a:
                    # was facing right - then make the transform turn left
                    if x_scale > 0:
                        self.entity.transform.scale_by(-x_scale, y_scale)

                # turn right
                elif event.key == pygame.K_d:
                    # was facing left
                    if x_scale < 0:
                        self.entity.transform.scale_by(-x_scale, y_scale)

            if self.entity.get_script("player climb").climbing:
                # turn left
                if event.key == pygame.K_a:
                    # was facing right then make the transform turn right
                    if x_scale > 0:
                        self.entity.transform.scale_by(-x_scale, y_scale)

                # turn right
                elif event.key == pygame.K_d:
                    # was facing left
                    if x_scale < 0:
                        self.entity.transform.scale_by(-x_scale, y_scale)

            # check that we are grounded- if so then JUMP
            if event.key == pygame.K_SPACE and self.grounded:
                self.entity.rigid_body.velocity.y = -self.v_speed
                self.entity.rigid_body.velocity.x *= 4/5.0

                # we are no longer grounded
                self.grounded = False

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d:
                self.moving = False

    def collision_event(self, other_collider):

        tag = other_collider.entity.tag

        # collided with a wall, floor, platform
        if tag == "wall" or tag == "floor" or tag == "platform" or "box":

            # hit from the top which means that this collider bottom side was hit by the other collider
            if PhysicsSystem.calc_box_hit_orientation(self.entity.collider, other_collider) == PhysicsSystem.bottom:
                self.grounded = True

        # collides with a crate
        # if other_collider.entity.tag == "box":
        #
        #     # check if the player hits the box from the sides
        #     side = PhysicsSystem.calc_box_hit_orientation(self.entity.collider, other_collider)
        #
        #     direction = 1
        #     # hit the other object from the left
        #     if side == PhysicsSystem.left:
        #         direction = -1
        #
        #     if side == PhysicsSystem.left or side == PhysicsSystem.right:
        #         if self.grounded and self.holding_crate:
        #             other_collider.entity.rigid_body.velocity.x = 4*self.h_speed/5.0 * direction

    def test_if_grounded(self):

        self.grounded = False

        # iterate through all the entities of the world
        for other in self.entity.world.entity_manager.entities:

            # make sure it is not itself
            if self.entity is not other:

                # check if the player collided with a wall, box, or platform
                tag = other.tag
                if tag == "wall" or tag == "platform" or tag == "box" or tag == "floor":

                    player = self.entity

                    temp_player_box = copy(player.collider.box)
                    temp_other_box = copy(other.collider.box)

                    # use the tolerance hit boxes to detect collision
                    player.collider.box = player.collider.tolerance_hitbox
                    other.collider.box = other.collider.tolerance_hitbox

                    player.collider.box.center = temp_player_box.center
                    other.collider.box.center = temp_other_box.center

                    # if the player collided with an element considered as ground, then ground the player
                    if PhysicsSystem.box2box_collision(player.collider, other.collider):

                        # check orientation of the collision
                        orientation = PhysicsSystem.calc_box_hit_orientation
                        if orientation(player.collider, other.collider) == PhysicsSystem.bottom:
                            self.grounded = True

                    # reset the collider boxes to the original ones
                    player.collider.box = temp_player_box
                    other.collider.box = temp_other_box

    def check_if_near_crate(self):


        result = (False, None)

        # check if the player is near a box
        for crate in self.entity.world.crates:

            # this code stops crates from being pushed inside of colliders such as walls
            for entity in self.entity.world.entity_manager.entities:

                # collider exists and is not a trigger
                valid_collider = entity.collider is not None and not entity.collider.is_trigger

                # dont consider the player or yourself during this collision test
                if valid_collider and entity is not self.entity and entity is not crate:

                    # collision occurs
                    if PhysicsSystem.box2box_collision(crate.collider, entity.collider):

                        # check of the collision occurred from the sides
                        side = PhysicsSystem.calc_box_hit_orientation(crate.collider, entity.collider)
                        if side == PhysicsSystem.left or side == PhysicsSystem.right:

                            # stop the crate from moving
                            return False, None

            player = self.entity

            temp_player_box = copy(player.collider.box)
            temp_other_box = copy(crate.collider.box)

            # use the tolerance hit boxes to detect collision
            player.collider.box = player.collider.tolerance_hitbox
            crate.collider.box = crate.collider.tolerance_hitbox

            player.collider.box.center = temp_player_box.center
            crate.collider.box.center = temp_other_box.center

            if PhysicsSystem.box2box_collision(player.collider, crate.collider):

                side = PhysicsSystem.calc_box_hit_orientation(player.collider, crate.collider)

                if side == PhysicsSystem.left or side == PhysicsSystem.right:
                    result = (True, crate)

                # some glitchy behavior required to offset the crate forward if the player moved the crate
                # towards to right and pushed the crate from the left side. Basically, we check the distance
                # between centers of the player and crate, and if the sum of the half-widths of both tolerance
                # hit boxes (of the player and create) are greater then the distance then we must offset
                # the create towards to right by some value

                distance = crate.transform.position - player.transform.position
                dx = abs(distance.x)
                x_tolerance_distance = crate.collider.tolerance_hitbox.w/2.0 + player.collider.tolerance_hitbox.w/2.0

                if dx < x_tolerance_distance-2:
                    shift = x_tolerance_distance - dx
                    # Player hits rate from his right and is pushing right
                    if side == PhysicsSystem.right and player.rigid_body.velocity.x > 0:
                        crate.transform.position.x += shift-20

                    elif side == PhysicsSystem.left and player.rigid_body.velocity.x < 0:
                        crate.transform.position.x -= shift-20

            # reset the collider boxes to the original ones
            player.collider.box = temp_player_box
            crate.collider.box = temp_other_box

        return result


class PlayerClimbing(BehaviorScript):

    def __init__(self, script_name):
        super(PlayerClimbing, self).__init__(script_name)

        self.climb_speed = 200.0
        self.move_up = False
        self.move_down = False
        self.climbing = False

    def update(self):
        keys = pygame.key.get_pressed()

        # check if we exited from the ladder collider
        if not self.colliding_with_ladder():
            self.climbing = False

            # reset the collider for side scrolling
            xs = self.entity.transform.scale.x
            self.entity.collider.set_offset(-12*xs, 10)

        # detect if the player wants to climb the ladder
        if keys[pygame.K_w]:
            self.move_up = True
        else:
            self.move_up = False

        if keys[pygame.K_s]:
            self.move_down = True
        else:
            self.move_down = False

        # if we are in a climbing state
        if self.climbing:

            # center the collider when climbing
            self.entity.collider.set_offset(0, 0)

            # disable gravity and un-pause climbing animation
            self.entity.rigid_body.gravity_scale = 0
            self.entity.animator.pause = False

            # move up or down the ladder
            if self.move_up:
                self.entity.rigid_body.velocity.y = -self.climb_speed
            elif self.move_down:
                self.entity.rigid_body.velocity.y = self.climb_speed

            # the player stays in place on the ladder
            else:
                self.entity.rigid_body.velocity.y = 0
                self.entity.animator.pause = True

        # we exited from the ladder - set gravity back to normal for the player
        # and un-pause the animator
        else:
            self.entity.rigid_body.gravity_scale = 1
            self.entity.animator.pause = False

    def collision_event(self, other_collider):

        # if the player is colliding with the ladder
        if other_collider.entity.tag == "ladder":
            grounded = self.entity.get_script("player plat move").grounded

            # if the player wants to move up or down then set climbing to true
            # and un-ground the player
            if self.move_up:

                # if the player climbs the ladder from mid air then slow him down
                # to attach him to the ladder
                if not grounded:
                    self.entity.rigid_body.velocity.x *= 0.1

                self.entity.get_script("player plat move").grounded = False
                self.climbing = True

            elif self.move_down:
                if not grounded:
                    self.entity.rigid_body.velocity.x *= 0.1

                self.entity.get_script("player plat move").grounded = False
                self.climbing = True

    def colliding_with_ladder(self):
        # check if the player is colliding with a ladder
        for ladder in self.entity.world.ladders:
            if PhysicsSystem.box2box_collision(self.entity.collider, ladder.collider):
                return True
        return False